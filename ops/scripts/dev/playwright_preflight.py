"""Preflight checks for admin Playwright managed-server runs.

The admin Playwright config starts both FastAPI and Vite unless
``PLAYWRIGHT_USE_EXTERNAL_SERVERS`` is enabled. This script checks the local
runtime assumptions before the browser runner is invoked, so environment
failures such as a missing repository virtualenv are diagnosed directly.

Examples:

    python ops/scripts/dev/playwright_preflight.py
    python ops/scripts/dev/playwright_preflight.py --json
    python ops/scripts/dev/playwright_preflight.py --include-private-paths
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_API_PORT = 8012
DEFAULT_UI_PORT = 3012
REQUIRED_BACKEND_MODULES = ("uvicorn", "fastapi", "sqlalchemy")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    summary: str
    detail: str = ""


def git_repo_root(start: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Unable to locate git repository root from {start}: {exc}") from exc
    return Path(result.stdout.strip()).resolve()


def placeholder_path(repo_root: Path, path: Path | None, include_private: bool) -> str:
    if path is None:
        return ""
    if path.resolve() == repo_root.resolve():
        return "<repo>"
    resolved = path.resolve() if path.exists() else path.absolute()
    if include_private:
        return str(resolved)
    try:
        rel = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return "<local-path>"
    return "<repo>/" + rel.as_posix()


def path_entry_exists(path: Path) -> bool:
    return path.exists() or os.path.lexists(path)


def check_path_exists(name: str, path: Path, repo_root: Path, include_private: bool) -> Check:
    shown = placeholder_path(repo_root, path, include_private)
    if path.exists():
        return Check(name, "pass", f"found {shown}")
    if os.path.lexists(path):
        return Check(name, "fail", f"path entry exists but target is unavailable: {shown}")
    return Check(name, "fail", f"missing {shown}")


def is_windows_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            return bool(is_junction())
        except OSError:
            return False
    return False


def describe_venv(repo_root: Path, include_private: bool, required: bool) -> Check:
    venv = repo_root / ".venv"
    if not path_entry_exists(venv):
        status = "fail" if required else "warn"
        return Check("repository-venv", status, "missing <repo>/.venv")

    link_kind = []
    if venv.is_symlink():
        link_kind.append("symlink")
    if is_windows_junction(venv):
        link_kind.append("junction")
    kind = "/".join(link_kind) if link_kind else "directory"

    detail = ""
    if link_kind:
        try:
            target = venv.resolve(strict=False)
        except OSError as exc:
            target = None
            detail = f"unable to resolve target: {exc}"
        if target is not None:
            detail = f"target={placeholder_path(repo_root, target, include_private)}"

    status = "pass" if venv.exists() else ("fail" if required else "warn")
    summary = f"<repo>/.venv exists ({kind})" if venv.exists() else f"<repo>/.venv entry exists but target is unavailable ({kind})"
    return Check("repository-venv", status, summary, detail)


def default_python(repo_root: Path) -> Path:
    if os.name == "nt":
        return repo_root / ".venv" / "Scripts" / "python.exe"
    return repo_root / ".venv" / "bin" / "python"


def selected_python(repo_root: Path) -> tuple[Path, str]:
    configured = os.environ.get("E2E_PYTHON")
    if configured:
        return Path(configured), "E2E_PYTHON"
    return default_python(repo_root), "playwright default"


def check_python_exists(repo_root: Path, include_private: bool) -> tuple[Check, Path | None]:
    python_path, source = selected_python(repo_root)
    shown = placeholder_path(repo_root, python_path, include_private)
    if python_path.exists():
        return Check("e2e-python", "pass", f"{source} exists: {shown}"), python_path
    return Check("e2e-python", "fail", f"{source} missing: {shown}"), None


def check_backend_imports(python_path: Path | None) -> Check:
    if python_path is None:
        return Check("backend-imports", "fail", "cannot check backend imports without a Python executable")

    code = (
        "import importlib.util, sys; "
        f"missing=[m for m in {REQUIRED_BACKEND_MODULES!r} if importlib.util.find_spec(m) is None]; "
        "print('\\n'.join(missing)); "
        "sys.exit(1 if missing else 0)"
    )
    try:
        result = subprocess.run(
            [str(python_path), "-c", code],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("backend-imports", "fail", "backend import check could not run", str(exc))

    missing = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode == 0 and not missing:
        return Check("backend-imports", "pass", "Python can import uvicorn, fastapi, and sqlalchemy")
    detail = result.stderr.strip()
    if missing:
        detail = f"missing modules: {', '.join(missing)}"
    return Check("backend-imports", "fail", "Python is missing backend dependencies", detail)


def check_command(name: str, command: str) -> Check:
    found = shutil.which(command)
    if found:
        return Check(name, "pass", f"{command} found on PATH")
    return Check(name, "fail", f"{command} not found on PATH")


def check_port(port: int) -> Check:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
    if result == 0:
        return Check(f"port-{port}", "warn", f"127.0.0.1:{port} already accepts TCP connections")
    return Check(f"port-{port}", "pass", f"127.0.0.1:{port} appears free")


def playwright_external_servers_enabled() -> bool:
    value = os.environ.get("PLAYWRIGHT_USE_EXTERNAL_SERVERS", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def status_code(checks: Iterable[Check]) -> int:
    has_fail = any(check.status == "fail" for check in checks)
    if has_fail:
        return 1
    has_warn = any(check.status == "warn" for check in checks)
    return 2 if has_warn else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to git rev-parse.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--include-private-paths",
        action="store_true",
        help="Print absolute local paths. Use only for ignored local notes under .agent-run/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else git_repo_root(Path.cwd())
    admin_root = repo_root / "apps" / "web" / "admin"
    vite_bin = admin_root / "node_modules" / "vite" / "bin" / "vite.js"
    playwright_config = admin_root / "playwright.config.cjs"
    package_lock = admin_root / "package-lock.json"

    use_managed_web_server = not playwright_external_servers_enabled()

    checks: list[Check] = [
        check_path_exists("admin-root", admin_root, repo_root, args.include_private_paths),
        check_path_exists("playwright-config", playwright_config, repo_root, args.include_private_paths),
        check_path_exists("admin-package-lock", package_lock, repo_root, args.include_private_paths),
        check_path_exists("vite-bin", vite_bin, repo_root, args.include_private_paths),
        describe_venv(repo_root, args.include_private_paths, use_managed_web_server),
        check_command("node", "node"),
        check_command("npm.cmd" if os.name == "nt" else "npm", "npm.cmd" if os.name == "nt" else "npm"),
        check_command("npx.cmd" if os.name == "nt" else "npx", "npx.cmd" if os.name == "nt" else "npx"),
    ]

    if use_managed_web_server:
        python_check, python_path = check_python_exists(repo_root, args.include_private_paths)
        checks.append(python_check)
        checks.append(check_backend_imports(python_path))
    else:
        python_path = None
        checks.append(
            Check(
                "e2e-python",
                "warn",
                "skipped because PLAYWRIGHT_USE_EXTERNAL_SERVERS is enabled",
                "managed webServer will not start the backend",
            )
        )
        checks.append(
            Check(
                "backend-imports",
                "warn",
                "skipped because PLAYWRIGHT_USE_EXTERNAL_SERVERS is enabled",
                "managed webServer will not start the backend",
            )
        )

    api_port = int(os.environ.get("E2E_API_PORT", DEFAULT_API_PORT))
    ui_port = int(os.environ.get("E2E_UI_PORT", DEFAULT_UI_PORT))
    checks.extend([check_port(api_port), check_port(ui_port)])

    code = status_code(checks)
    payload = {
        "repo_root": placeholder_path(repo_root, repo_root, args.include_private_paths),
        "admin_root": placeholder_path(repo_root, admin_root, args.include_private_paths),
        "managed_web_server": use_managed_web_server,
        "exit_code": code,
        "checks": [asdict(check) for check in checks],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("# Admin Playwright Preflight")
        print(f"Repository: {payload['repo_root']}")
        print(f"Admin root: {payload['admin_root']}")
        print(f"Managed webServer: {payload['managed_web_server']}")
        for check in checks:
            detail = f" ({check.detail})" if check.detail else ""
            print(f"[{check.status.upper()}] {check.name}: {check.summary}{detail}")
        if code == 1:
            print("Result: failed preflight. Fix the failed items or set PLAYWRIGHT_USE_EXTERNAL_SERVERS=1 with known-good servers.")
        elif code == 2:
            print("Result: preflight passed with warnings. Confirm warnings before running Playwright.")
        else:
            print("Result: preflight passed.")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

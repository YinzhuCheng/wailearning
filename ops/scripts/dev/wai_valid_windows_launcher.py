from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_EXE = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LAUNCH_LOG = STATE_DIR / "WAI-VALID-launcher.log"
MONITOR_LAUNCHER_CMD = STATE_DIR / "WAI-VALID-launch-monitor.cmd"


def _windows_creation_flags(*flags: int) -> int:
    value = 0
    for flag in flags:
        value |= flag
    return value


DETACHED_FLAGS = _windows_creation_flags(
    getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200),
)
BACKGROUND_FLAGS = DETACHED_FLAGS | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
VISIBLE_FLAGS = DETACHED_FLAGS | getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)


def write_launch_log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LAUNCH_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    background = subparsers.add_parser("background", help="Start a detached background process.")
    background.add_argument("script_path", help="Absolute or repository-relative script path to launch.")
    background.add_argument("script_args", nargs=argparse.REMAINDER, help="Optional script arguments.")

    return parser.parse_args()


def _normalize_script_path(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _build_background_wrapper(script: Path, script_args: list[str]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    wrapper_path = STATE_DIR / f"WAI-VALID-background-launch-{int(time.time() * 1000)}.ps1"
    wrapper_lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$scriptPath = {_ps_single_quote(str(script))}",
        "$scriptArgs = @(",
    ]
    wrapper_lines.extend(f"    {_ps_single_quote(arg)}" for arg in script_args)
    wrapper_lines.extend(
        [
            ")",
            "& $scriptPath @scriptArgs",
            "",
        ]
    )
    wrapper_path.write_text("\n".join(wrapper_lines), encoding="utf-8")
    return wrapper_path


def launch_background(script_path: str, script_args: list[str]) -> int:
    script = _normalize_script_path(script_path)
    if not script.exists():
        raise SystemExit(f"Script not found: {script}")
    wrapper = _build_background_wrapper(script, script_args)
    args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper),
    ]
    write_launch_log(f"background script={script}")
    write_launch_log(f"background wrapper={wrapper}")
    write_launch_log(f"background script_args={script_args!r}")
    write_launch_log(f"background args={args!r}")
    subprocess.Popen(
        args,
        cwd=str(REPO_ROOT),
        creationflags=BACKGROUND_FLAGS,
        close_fds=True,
        env=os.environ.copy(),
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "background":
        return launch_background(args.script_path, args.script_args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

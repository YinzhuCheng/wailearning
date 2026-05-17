from __future__ import annotations

import argparse
import os
import subprocess
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

    monitor = subparsers.add_parser("monitor", help="Open a visible monitor window.")
    monitor.add_argument("--run-id", help="Optional explicit run id to pin the monitor to.")

    background = subparsers.add_parser("background", help="Start a detached background process.")
    background.add_argument("script_path", help="Absolute or repository-relative script path to launch.")
    background.add_argument("script_args", nargs=argparse.REMAINDER, help="Optional script arguments.")

    return parser.parse_args()


def _normalize_script_path(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def launch_monitor(run_id: str | None) -> int:
    monitor_script = REPO_ROOT / "ops" / "scripts" / "dev" / "wai_valid_monitor.py"
    cmd = f'"{PYTHON_EXE}" -u "{monitor_script}"'
    if run_id:
        cmd += f' --run-id "{run_id}"'
    launcher_body = "@echo off\r\n" + f"title WAI-VALID-monitor\r\n{cmd}\r\n"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MONITOR_LAUNCHER_CMD.write_text(launcher_body, encoding="utf-8")
    write_launch_log(f"monitor cmd={cmd}")
    subprocess.Popen(
        ["cmd.exe", "/c", "start", '"WAI-VALID-monitor"', str(MONITOR_LAUNCHER_CMD)],
        cwd=str(REPO_ROOT),
        creationflags=DETACHED_FLAGS,
        close_fds=True,
    )
    return 0


def launch_background(script_path: str, script_args: list[str]) -> int:
    script = _normalize_script_path(script_path)
    if not script.exists():
        raise SystemExit(f"Script not found: {script}")
    args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    args.extend(script_args)
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
    if args.command == "monitor":
        return launch_monitor(args.run_id)
    if args.command == "background":
        return launch_background(args.script_path, args.script_args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

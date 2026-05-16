from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wai_valid_render import render_progress_snapshot

REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"
MONITOR_TITLE = "WAI-VALID-monitor"
DEFAULT_REFRESH_SECONDS = 2


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_current_run() -> tuple[Path | None, str]:
    current_run = STATE_DIR / "WAI-VALID-current-run.json"
    if current_run.exists():
        payload = load_json(current_run)
        if payload:
            progress = payload.get("progress_file")
            if progress:
                p = Path(str(progress))
                if p.exists():
                    return p, str(payload.get("run_id") or p.parent.name)

    candidates = []
    for path in LOG_ROOT.glob("*/progress.json"):
        try:
            candidates.append((path.stat().st_mtime, path))
        except FileNotFoundError:
            continue
    if not candidates:
        return None, "n/a"
    candidates.sort(key=lambda item: item[0], reverse=True)
    p = candidates[0][1]
    return p, p.parent.name


def render_progress(progress_path: Path, run_id: str) -> None:
    payload = load_json(progress_path) or {}
    payload["events_file_path"] = str(progress_path.with_name("events.log"))
    render_progress_snapshot(payload, run_id)


def main() -> int:
    try:
        import ctypes  # noqa: WPS433

        ctypes.windll.kernel32.SetConsoleTitleW(MONITOR_TITLE)
    except Exception:
        pass

    while True:
        if os.name == "nt":
            print("\n" + "=" * 100)
        else:
            print("\033[2J\033[H", end="")
        progress_path, run_id = find_current_run()
        if progress_path is None:
            print("[WAI-VALID] waiting for a progress file...")
        else:
            try:
                render_progress(progress_path, run_id)
            except Exception as exc:
                print("\n" + "=" * 100)
                print(f"[WAI-VALID] progress render error: {exc}")
        sys.stdout.flush()
        time.sleep(DEFAULT_REFRESH_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())

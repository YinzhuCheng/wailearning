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
CURRENT_RUN_PATH = STATE_DIR / "WAI-VALID-current-run.json"
MONITOR_TITLE = "WAI-VALID-monitor"
DEFAULT_REFRESH_SECONDS = 2
ACTIVE_STALE_AFTER_SECONDS = 15


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def progress_score(progress_path: Path) -> tuple[int, int, float]:
    payload = load_json(progress_path) or {}
    total = int(payload.get("total") or 0)
    done = int(payload.get("completed_count") or payload.get("passed_count") or 0)
    running = len(list(payload.get("running") or []))
    queue = int(payload.get("queue_remaining") or 0)
    try:
        mtime = progress_path.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    age_seconds = max(0.0, time.time() - mtime)
    is_recent = 1 if age_seconds <= ACTIVE_STALE_AFTER_SECONDS else 0
    has_unfinished_work = 1 if (queue > 0 or (total and done < total)) else 0
    is_active = 1 if (running > 0 or (has_unfinished_work and is_recent)) else 0
    return running, is_active, mtime


def write_current_run(progress_path: Path, run_id: str) -> None:
    run_dir = progress_path.parent
    payload = {
        "run_id": run_id,
        "progress_file": str(progress_path),
        "events_file": str(run_dir / "events.log"),
        "results_file": str(run_dir / "results.jsonl"),
        "run_config_file": str(run_dir / "run-config.json"),
        "mode": "monitor-autoselect",
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_current_run() -> tuple[Path | None, str]:
    pinned_progress: Path | None = None
    pinned_run_id = "n/a"
    if CURRENT_RUN_PATH.exists():
        payload = load_json(CURRENT_RUN_PATH)
        if payload:
            progress = payload.get("progress_file")
            if progress:
                p = Path(str(progress))
                if p.exists():
                    pinned_progress = p
                    pinned_run_id = str(payload.get("run_id") or p.parent.name)

    candidates = []
    for path in LOG_ROOT.glob("*/progress.json"):
        try:
            candidates.append((progress_score(path), path))
        except FileNotFoundError:
            continue
    if pinned_progress is None and not candidates:
        return None, "n/a"

    best_progress: Path | None = None
    best_run_id = "n/a"
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        best_progress = candidates[0][1]
        best_run_id = best_progress.parent.name

    if pinned_progress is not None:
        pinned_running, pinned_active, pinned_mtime = progress_score(pinned_progress)
        if pinned_active:
            return pinned_progress, pinned_run_id
        if best_progress is None:
            return pinned_progress, pinned_run_id
        best_running, best_active, best_mtime = progress_score(best_progress)
        if best_progress != pinned_progress and (
            best_running > pinned_running
            or best_active > pinned_active
            or best_mtime > pinned_mtime
        ):
            write_current_run(best_progress, best_run_id)
            return best_progress, best_run_id
        return pinned_progress, pinned_run_id

    if best_progress is not None:
        write_current_run(best_progress, best_run_id)
        return best_progress, best_run_id
    return None, "n/a"


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

    print("[WAI-VALID] monitor starting...", flush=True)

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

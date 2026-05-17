from __future__ import annotations

import argparse
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
MONITOR_PID_PATH = STATE_DIR / "WAI-VALID-monitor.pid"
MONITOR_TITLE = "WAI-VALID-monitor"
DEFAULT_REFRESH_SECONDS = 2
ACTIVE_STALE_AFTER_SECONDS = 15


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def run_preference(run_name: str) -> int:
    normalized = run_name.lower()
    if "backend-only-rerun" in normalized:
        return 3
    if "backend-only" in normalized:
        return 2
    if "round2" in normalized:
        return 1
    return 0


def progress_score(progress_path: Path) -> tuple[int, int, int, float]:
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
    has_live_work = 1 if (running > 0 or has_unfinished_work) else 0
    is_active = 1 if (is_recent and has_live_work) else 0
    is_finished = 1 if (total > 0 and done >= total and queue == 0 and running == 0) else 0
    freshness_rank = 2 if is_active else (1 if is_finished else 0)
    return freshness_rank, run_preference(progress_path.parent.name), running, mtime


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


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes  # noqa: WPS433

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) == 0:
                    return False
                return exit_code.value == 259
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def claim_monitor_ownership() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    current_pid = os.getpid()
    existing_pid: int | None = None
    if MONITOR_PID_PATH.exists():
        try:
            existing_pid = int(MONITOR_PID_PATH.read_text(encoding="utf-8").strip())
        except Exception:
            existing_pid = None
    if existing_pid and existing_pid != current_pid and _pid_is_alive(existing_pid):
        raise SystemExit(f"WAI-VALID monitor already running with pid={existing_pid}")
    MONITOR_PID_PATH.write_text(str(current_pid), encoding="utf-8")


def release_monitor_ownership() -> None:
    if not MONITOR_PID_PATH.exists():
        return
    try:
        recorded_pid = int(MONITOR_PID_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        recorded_pid = None
    if recorded_pid in (None, os.getpid()):
        try:
            MONITOR_PID_PATH.unlink()
        except FileNotFoundError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Prefer a specific run id instead of auto-discovery.")
    return parser.parse_args()


def find_current_run(forced_run_id: str | None = None) -> tuple[Path | None, str]:
    if forced_run_id:
        run_name = forced_run_id if forced_run_id.startswith("WAI-VALID-") else f"WAI-VALID-{forced_run_id}"
        forced_progress = LOG_ROOT / run_name / "progress.json"
        if forced_progress.exists():
            write_current_run(forced_progress, run_name)
            return forced_progress, run_name
        return None, run_name
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
        pinned_rank, pinned_pref, pinned_running, pinned_mtime = progress_score(pinned_progress)
        if pinned_rank >= 2:
            return pinned_progress, pinned_run_id
        if best_progress is None:
            return pinned_progress, pinned_run_id
        best_rank, best_pref, best_running, best_mtime = progress_score(best_progress)
        if best_progress != pinned_progress and (
            best_rank > pinned_rank
            or (
                best_rank == pinned_rank
                and (
                    best_pref > pinned_pref
                    or (
                        best_pref == pinned_pref
                        and (
                            best_running > pinned_running
                    or best_mtime > pinned_mtime
                        )
                    )
                )
            )
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
    args = parse_args()
    claim_monitor_ownership()
    try:
        import ctypes  # noqa: WPS433

        ctypes.windll.kernel32.SetConsoleTitleW(MONITOR_TITLE)
    except Exception:
        pass

    print("[WAI-VALID] monitor starting...", flush=True)

    try:
        while True:
            if os.name == "nt":
                print("\n" + "=" * 100)
            else:
                print("\033[2J\033[H", end="")
            progress_path, run_id = find_current_run(args.run_id)
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
    finally:
        release_monitor_ownership()


if __name__ == "__main__":
    raise SystemExit(main())

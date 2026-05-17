from __future__ import annotations

import json
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"
ACTIVE_STALE_AFTER_SECONDS = 15


def _progress_score(progress_path: Path) -> tuple[int, int, float]:
    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return (0, 0, progress_path.stat().st_mtime)

    total = int(payload.get("total") or 0)
    done = int(payload.get("completed_count") or 0)
    running = len(list(payload.get("running") or []))
    queue = int(payload.get("queue_remaining") or 0)
    mtime = progress_path.stat().st_mtime
    age_seconds = max(0.0, time.time() - mtime)
    is_recent = 1 if age_seconds <= ACTIVE_STALE_AFTER_SECONDS else 0
    has_unfinished_work = 1 if (queue > 0 or (total and done < total)) else 0
    is_active = 1 if (running > 0 or (has_unfinished_work and is_recent)) else 0
    return (running, is_active, mtime)


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    candidates = []
    for progress in LOG_ROOT.glob("*/progress.json"):
        try:
            candidates.append((_progress_score(progress), progress))
        except FileNotFoundError:
            continue
    if not candidates:
        raise SystemExit("No progress.json found under .agent-run/logs/")

    candidates.sort(key=lambda item: item[0], reverse=True)
    progress_path = candidates[0][1]
    run_dir = progress_path.parent
    events_path = run_dir / "events.log"

    payload = {
        "run_id": run_dir.name,
        "progress_file": str(progress_path),
        "events_file": str(events_path),
        "mode": "visible-monitor",
    }
    out = STATE_DIR / "WAI-VALID-current-run.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

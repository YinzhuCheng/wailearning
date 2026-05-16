from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"


def _progress_score(progress_path: Path) -> tuple[int, float]:
    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return (0, progress_path.stat().st_mtime)

    total = int(payload.get("total") or 0)
    done = int(payload.get("completed_count") or 0)
    running = len(list(payload.get("running") or []))
    queue = int(payload.get("queue_remaining") or 0)
    is_active = 1 if (running > 0 or queue > 0 or (total and done < total)) else 0
    return (is_active, progress_path.stat().st_mtime)


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

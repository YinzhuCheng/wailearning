from __future__ import annotations

import json
import os
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"
MONITOR_TITLE = "WAI-VALID-monitor"
DEFAULT_REFRESH_SECONDS = 2


def clear_screen() -> None:
    os.system("cls")


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


def tail_lines(path: Path, count: int = 10) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-count:]
    except Exception:
        return []


def render_progress(progress_path: Path, run_id: str) -> None:
    payload = load_json(progress_path) or {}
    total = int(payload.get("total") or 0)
    done = int(payload.get("completed_count") or payload.get("passed_count") or 0)
    failed = int(payload.get("failed_count") or 0)
    running = list(payload.get("running") or [])
    queue = int(payload.get("queue_remaining") or 0)
    active_block = str(payload.get("block") or payload.get("active_block") or "")
    concurrency = payload.get("concurrency") or payload.get("block_concurrency") or ""
    regression_mode = str(payload.get("regression_mode") or "n/a")
    report = payload.get("report") or {}
    block_report = report.get("blocks") or {}
    origin_report = report.get("origins") or {}
    running_slots = payload.get("running_slots") or []
    pct = int(round((done / total) * 100)) if total else 0
    bar_len = 30
    filled = min(bar_len, max(0, int((pct / 100) * bar_len)))
    bar = "#" * filled + "-" * (bar_len - filled)

    print(f"[WAI-VALID] [{bar}] {pct}%")
    print(f"run={run_id}")
    print(f"block={active_block or 'n/a'} concurrency={concurrency or 'n/a'} regression={regression_mode}")
    print(f"passed={done}/{total} running={len(running)} failed={failed} queue={queue}")
    if payload.get("updated_at"):
        print(f"updated={payload['updated_at']}")
    print(
        "origins:"
        f" primary={origin_report.get('primary_total', 0)}"
        f" regression={origin_report.get('regression_total', 0)}"
        f" retry={origin_report.get('retry_total', 0)}"
    )
    print()
    print("running slots:")
    if running_slots:
        for slot in running_slots:
            print(
                f" - [{slot.get('block', 'n/a')}] {slot.get('shard', 'n/a')}"
                f" origin={slot.get('origin', 'n/a')}"
            )
    else:
        print(" - none")
    print()
    print("blocks:")
    for block_name, block_payload in block_report.items():
        print(
            f" - {block_name}:"
            f" pass={block_payload.get('completed_count', 0)}/{block_payload.get('total', 0)}"
            f" fail={block_payload.get('failed_count', 0)}"
            f" run={block_payload.get('running_count', 0)}"
            f" queue={block_payload.get('queue_remaining', 0)}"
            f" conc={block_payload.get('configured_concurrency', 'n/a')}"
        )
    print()
    print("recent events:")
    events_file = progress_path.with_name("events.log")
    for line in tail_lines(events_file, 10):
        print(line)


def main() -> int:
    try:
        import ctypes  # noqa: WPS433

        ctypes.windll.kernel32.SetConsoleTitleW(MONITOR_TITLE)
    except Exception:
        pass

    while True:
        clear_screen()
        progress_path, run_id = find_current_run()
        if progress_path is None:
            print("[WAI-VALID] waiting for a progress file...")
        else:
            try:
                render_progress(progress_path, run_id)
            except Exception as exc:
                print(f"[WAI-VALID] progress render error: {exc}")
        time.sleep(DEFAULT_REFRESH_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())

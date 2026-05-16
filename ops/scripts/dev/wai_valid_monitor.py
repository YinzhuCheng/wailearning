from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"
MONITOR_TITLE = "WAI-VALID-monitor"
DEFAULT_REFRESH_SECONDS = 2


def clear_screen() -> None:
    # Some Windows consoles intermittently render a blank screen after repeated
    # cls calls from a long-lived Python loop. Prefer a visible section break.
    try:
        if os.name == "nt":
            print("\n" + "=" * 100)
        else:
            print("\033[2J\033[H", end="")
    except Exception:
        print("\n" + "=" * 100)


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


def format_block_name(name: str) -> str:
    return name.replace("-", " ")


def sort_blocks(block_report: dict) -> list[tuple[str, dict]]:
    return sorted(block_report.items(), key=lambda item: item[0])


def render_header(pct: int, run_id: str, active_block: str, concurrency: object, regression_mode: str, updated_at: str | None) -> None:
    bar_len = 30
    filled = min(bar_len, max(0, int((pct / 100) * bar_len)))
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"[WAI-VALID] [{bar}] {pct}%")
    print(f"run={run_id}")
    print(
        f"mode={regression_mode}  "
        f"active_block={format_block_name(active_block) if active_block else 'n/a'}  "
        f"active_concurrency={concurrency or 'n/a'}"
    )
    if updated_at:
        print(f"updated={updated_at}")


def render_summary(done: int, failed: int, total: int, running_count: int, queue: int, origin_report: dict) -> None:
    print()
    print("summary:")
    print(
        f" - passed={done}/{total}"
        f" failed={failed}"
        f" running={running_count}"
        f" queue={queue}"
    )
    print(
        f" - origins:"
        f" primary={origin_report.get('primary_total', 0)}"
        f" regression={origin_report.get('regression_total', 0)}"
        f" retry={origin_report.get('retry_total', 0)}"
    )


def render_blocks(block_report: dict) -> None:
    print()
    print("blocks:")
    for block_name, block_payload in sort_blocks(block_report):
        print(
            f" - {format_block_name(block_name)}"
            f" | pass {block_payload.get('completed_count', 0)}/{block_payload.get('total', 0)}"
            f" | fail {block_payload.get('failed_count', 0)}"
            f" | run {block_payload.get('running_count', 0)}"
            f" | queue {block_payload.get('queue_remaining', 0)}"
            f" | conc {block_payload.get('configured_concurrency', 'n/a')}"
        )
        origins = block_payload.get("origins") or {}
        print(
            f"   origins: primary={origins.get('primary', 0)}"
            f" regression={origins.get('regression', 0)}"
            f" retry={origins.get('retry', 0)}"
        )
        running_slots = block_payload.get("running_slots") or []
        if running_slots:
            print("   slots:")
            for slot in running_slots:
                print(
                    f"    - {slot.get('shard', 'n/a')}"
                    f" [{slot.get('origin', 'n/a')}]"
                )


def render_running_slots(running_slots: list[dict]) -> None:
    print()
    print("running slots:")
    if not running_slots:
        print(" - none")
        return
    for slot in running_slots:
        print(
            f" - {slot.get('shard', 'n/a')}"
            f" | block={format_block_name(str(slot.get('block', 'n/a')))}"
            f" | origin={slot.get('origin', 'n/a')}"
            f" | detail={slot.get('origin_detail', 'n/a')}"
        )


def render_recent_events(events_file: Path) -> None:
    print()
    print("recent events:")
    for line in tail_lines(events_file, 12):
        print(f" - {line}")


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
    events_file = progress_path.with_name("events.log")
    pct = int(round((done / total) * 100)) if total else 0
    render_header(pct, run_id, active_block, concurrency, regression_mode, payload.get("updated_at"))
    render_summary(done, failed, total, len(running), queue, origin_report)
    render_blocks(block_report)
    render_running_slots(running_slots)
    render_recent_events(events_file)


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
        sys.stdout.flush()
        time.sleep(DEFAULT_REFRESH_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())

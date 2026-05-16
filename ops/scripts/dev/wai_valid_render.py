from __future__ import annotations

from pathlib import Path


def format_block_name(name: str) -> str:
    return name.replace("-", " ")


def tail_lines(path: Path, count: int = 10) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-count:]
    except Exception:
        return []


def sort_blocks(block_report: dict) -> list[tuple[str, dict]]:
    return sorted(block_report.items(), key=lambda item: item[0])


def render_header(
    pct: int,
    run_id: str,
    active_block: str,
    concurrency: object,
    regression_mode: str,
    updated_at: str | None,
) -> None:
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


def render_progress_snapshot(progress_payload: dict, run_id: str) -> None:
    total = int(progress_payload.get("total") or 0)
    done = int(progress_payload.get("completed_count") or progress_payload.get("passed_count") or 0)
    failed = int(progress_payload.get("failed_count") or 0)
    running = list(progress_payload.get("running") or [])
    queue = int(progress_payload.get("queue_remaining") or 0)
    active_block = str(progress_payload.get("block") or progress_payload.get("active_block") or "")
    concurrency = progress_payload.get("concurrency") or progress_payload.get("block_concurrency") or ""
    regression_mode = str(progress_payload.get("regression_mode") or "n/a")
    report = progress_payload.get("report") or {}
    block_report = report.get("blocks") or {}
    origin_report = report.get("origins") or {}
    running_slots = progress_payload.get("running_slots") or []
    pct = int(round((done / total) * 100)) if total else 0
    render_header(pct, run_id, active_block, concurrency, regression_mode, progress_payload.get("updated_at"))
    render_summary(done, failed, total, len(running), queue, origin_report)
    render_blocks(block_report)
    render_running_slots(running_slots)
    events_file_value = progress_payload.get("events_file_path")
    if events_file_value:
        render_recent_events(Path(str(events_file_value)))
    else:
        print()
        print("recent events:")
        print(" - n/a")

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wai_valid_render import render_progress_snapshot


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_EXE = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
STATE_DIR = REPO_ROOT / ".agent-run" / "validation-daemon"
LOG_ROOT = REPO_ROOT / ".agent-run" / "logs"
PID_PATH = STATE_DIR / "WAI-VALID-supervisor.pid"
STATE_PATH = STATE_DIR / "WAI-VALID-state.json"
QUEUE_PATH = STATE_DIR / "WAI-VALID-queue.json"
CURRENT_RUN_PATH = STATE_DIR / "WAI-VALID-current-run.json"
HEARTBEAT_SECONDS = 2

PG_BIN = Path(r"C:\Users\bloom\tools\postgres\pgsql\bin")
POSTGRES_EXE = PG_BIN / "postgres.exe"
PSQL_EXE = PG_BIN / "psql.exe"
INITDB_EXE = PG_BIN / "initdb.exe"


@dataclass
class Task:
    shard: str
    kind: str
    block: str
    port: int | None = None
    aux_port: int | None = None
    origin: str = "primary"
    origin_detail: str = "direct"
    target: str | None = None
    source_path: str | None = None


@dataclass
class RunningTask:
    task: Task
    proc: subprocess.Popen[Any]
    log_path: Path
    err_path: Path
    run_dir: Path | None
    started_at: float


@dataclass
class BlockSpec:
    name: str
    concurrency: int
    paths: list[str]
    path_metadata: dict[str, dict[str, str]] | None = None


REGRESSION_EXPANSIONS: dict[str, dict[str, list[str]]] = {
    "homework": {
        "medium": [
            "tests/backend/homework/test_homework_llm_grading.py",
            "tests/behavior/test_homework_lifecycle_llm_behavior.py",
        ],
        "heavy": [
            "tests/backend/homework/test_homework_llm_grading.py",
            "tests/behavior/test_homework_lifecycle_llm_behavior.py",
            "tests/behavior/test_course_roster_homework_edge_behavior.py",
            "tests/behavior/test_material_chapters_notifications_homework_flow.py",
        ],
    },
    "llm": {
        "medium": [
            "tests/backend/homework/test_homework_llm_grading.py",
            "tests/behavior/test_homework_lifecycle_llm_behavior.py",
        ],
        "heavy": [
            "tests/backend/homework/test_homework_llm_grading.py",
            "tests/behavior/test_homework_lifecycle_llm_behavior.py",
            "tests/behavior/test_per_course_llm_quota_advanced_behavior.py",
            "tests/behavior/test_regression_llm_quota_behavior.py",
        ],
    },
    "notifications": {
        "medium": [
            "tests/behavior/test_notification_sync_api_edge_behavior.py",
        ],
        "heavy": [
            "tests/behavior/test_notification_sync_api_edge_behavior.py",
            "tests/behavior/test_material_chapters_notifications_homework_flow.py",
        ],
    },
    "discussions": {
        "medium": [
            "tests/behavior/test_discussion_api_behavior.py",
        ],
        "heavy": [
            "tests/behavior/test_discussion_api_behavior.py",
            "tests/behavior/test_discussion_api_advanced_behavior.py",
            "tests/behavior/test_discussion_llm_retry_behavior.py",
        ],
    },
    "roster": {
        "medium": [
            "tests/backend/courses/test_student_course_roster_behavior.py",
        ],
        "heavy": [
            "tests/backend/courses/test_student_course_roster_behavior.py",
            "tests/behavior/test_course_roster_homework_edge_behavior.py",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Pytest shard paths or directories to supervise.")
    parser.add_argument("--run-id", required=True, help="Logical run id. 'WAI-VALID-' is added if missing.")
    parser.add_argument("--concurrency", type=int, help="Maximum concurrent shards for a single-block run.")
    parser.add_argument(
        "--block",
        default="auto",
        help="Optional logical block name for progress reporting. Defaults to auto classification.",
    )
    parser.add_argument(
        "--block-spec",
        action="append",
        default=[],
        help="Block definition in the form block-name:concurrency:path1,path2,path3 . May be repeated.",
    )
    parser.add_argument(
        "--postgres-base-port",
        type=int,
        default=15460,
        help="Base TCP port for PostgreSQL-isolated shards.",
    )
    parser.add_argument(
        "--replace-run-dir",
        action="store_true",
        help="Delete an existing run directory before starting. Use for intentional fresh reruns only.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=HEARTBEAT_SECONDS,
        help="Rewrite progress at least this often even when no shard starts or ends.",
    )
    parser.add_argument(
        "--regression-mode",
        choices=("light", "medium", "heavy"),
        default="medium",
        help="Logical regression intensity label for reporting and future expansion rules.",
    )
    parser.add_argument(
        "--no-console-report",
        action="store_true",
        help="Disable supervisor-side live console reporting.",
    )
    args = parser.parse_args()
    if args.block_spec:
        if args.concurrency is not None:
            raise SystemExit("--concurrency cannot be combined with --block-spec.")
        if args.paths:
            raise SystemExit("Positional paths cannot be combined with --block-spec.")
    else:
        if args.concurrency is None:
            raise SystemExit("--concurrency is required when --block-spec is not used.")
        if not args.paths:
            raise SystemExit("At least one path is required for a single-block run.")
    return args


def ensure_prefixed_run_id(run_id: str) -> str:
    return run_id if run_id.startswith("WAI-VALID-") else f"WAI-VALID-{run_id}"


def ensure_python() -> None:
    if not PYTHON_EXE.exists():
        raise SystemExit(f"Missing repository venv interpreter: {PYTHON_EXE}")


def is_valid_test_target(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").strip()
    if not normalized:
        return False
    parts = [part for part in normalized.split("/") if part]
    if any(part == "__pycache__" for part in parts):
        return False
    if any(part.startswith(".") for part in parts):
        return False
    return True


def safe_name(shard: str) -> str:
    out = shard
    for ch in "\\/:. ":
        out = out.replace(ch, "_")
    out = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in out)
    digest = hashlib.sha1(shard.encode("utf-8")).hexdigest()[:12]
    max_prefix_length = 72
    if len(out) > max_prefix_length:
        out = out[:max_prefix_length].rstrip("_")
    return f"{out}__{digest}"


def normalize_path_text(path_text: str) -> str:
    return path_text.replace("\\", "/").strip()


def is_pytest_file_target(path_text: str) -> bool:
    normalized = normalize_path_text(path_text)
    return normalized.endswith(".py") and "::" not in normalized


def collect_pytest_nodeids(path_text: str) -> list[str]:
    normalized = normalize_path_text(path_text)
    if "::" in normalized:
        return [normalized]
    proc = subprocess.run(
        [str(PYTHON_EXE), "-m", "pytest", normalized, "--collect-only", "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    if proc.returncode != 0:
        combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        raise SystemExit(f"pytest collect-only failed for {normalized}:\n{combined}")
    nodeids: list[str] = []
    for line in proc.stdout.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("="):
            continue
        if candidate.endswith(" collected"):
            continue
        if "::" not in candidate:
            continue
        nodeids.append(candidate.replace("\\", "/"))
    if not nodeids:
        raise SystemExit(f"pytest collect-only returned no nodeids for {normalized}")
    return nodeids


def classify_tasks(paths: list[str], block_name: str, postgres_base_port: int) -> list[Task]:
    tasks: list[Task] = []
    pg_index = 0
    pw_index = 0
    for raw_path in paths:
        if not is_valid_test_target(raw_path):
            continue
        path = normalize_path_text(raw_path)
        if path.startswith("tests/postgres/"):
            postgres_targets = collect_pytest_nodeids(path) if is_pytest_file_target(path) else [path]
            for target in postgres_targets:
                tasks.append(
                    Task(
                        shard=target,
                        kind="postgres",
                        block=block_name if block_name != "auto" else "backend-postgres-sensitive",
                        port=postgres_base_port + pg_index,
                        origin="primary",
                        origin_detail="direct-target",
                        target=target,
                        source_path=path,
                    )
                )
                pg_index += 1
            continue
        if path.startswith("tests/e2e/web-school/") and path.endswith(".spec.js"):
            api_port = 18112 + pw_index
            ui_port = 19112 + pw_index
            tasks.append(
                Task(
                    shard=path,
                    kind="playwright",
                    block=block_name if block_name != "auto" else "playwright-school-e2e",
                    port=api_port,
                    aux_port=ui_port,
                    origin="primary",
                    origin_detail="direct-target",
                    target=path,
                    source_path=path,
                )
            )
            pw_index += 1
            continue
        if path.startswith("tests/behavior/"):
            behavior_targets = collect_pytest_nodeids(path) if is_pytest_file_target(path) else [path]
            for target in behavior_targets:
                tasks.append(
                    Task(
                        shard=target,
                        kind="pytest",
                        block=block_name if block_name != "auto" else "behavior",
                        origin="primary",
                        origin_detail="direct-target",
                        target=target,
                        source_path=path,
                    )
                )
            continue
        if path.startswith("tests/backend/"):
            backend_targets = collect_pytest_nodeids(path) if is_pytest_file_target(path) else [path]
            for target in backend_targets:
                tasks.append(
                    Task(
                        shard=target,
                        kind="pytest",
                        block=block_name if block_name != "auto" else "backend-sqlite-compatible",
                        origin="primary",
                        origin_detail="direct-target",
                        target=target,
                        source_path=path,
                    )
                )
            continue
        generic_targets = collect_pytest_nodeids(path) if is_pytest_file_target(path) else [path]
        for target in generic_targets:
            tasks.append(
                Task(
                    shard=target,
                    kind="pytest",
                    block=block_name if block_name != "auto" else "generic",
                    origin="primary",
                    origin_detail="direct-target",
                    target=target,
                    source_path=path,
                )
            )
    return tasks


def parse_block_specs(specs: list[str]) -> list[BlockSpec]:
    block_specs: list[BlockSpec] = []
    for raw_spec in specs:
        if raw_spec.count(":") < 2:
            raise SystemExit(f"Invalid --block-spec: {raw_spec}")
        name, concurrency_text, path_blob = raw_spec.split(":", 2)
        name = name.strip()
        if not name:
            raise SystemExit(f"Invalid --block-spec name: {raw_spec}")
        try:
            concurrency = int(concurrency_text.strip())
        except ValueError as exc:
            raise SystemExit(f"Invalid --block-spec concurrency: {raw_spec}") from exc
        paths = [path.strip() for path in path_blob.split(",") if path.strip()]
        if not paths:
            raise SystemExit(f"Invalid --block-spec paths: {raw_spec}")
        block_specs.append(BlockSpec(name=name, concurrency=concurrency, paths=paths, path_metadata={}))
    return block_specs


def build_block_specs(args: argparse.Namespace) -> list[BlockSpec]:
    if args.block_spec:
        return parse_block_specs(args.block_spec)
    block_name = args.block if args.block != "auto" else "auto"
    return [BlockSpec(name=block_name, concurrency=int(args.concurrency), paths=list(args.paths), path_metadata={})]


def classify_domain_tags(path: str) -> set[str]:
    normalized = path.replace("\\", "/")
    tags: set[str] = set()
    for tag in ("homework", "llm", "notifications", "discussions", "roster"):
        if tag in normalized:
            tags.add(tag)
    return tags


def infer_block_name_from_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("tests/postgres/"):
        return "backend-postgres-sensitive"
    if normalized.startswith("tests/behavior/"):
        return "behavior"
    if normalized.startswith("tests/e2e/"):
        return "playwright-e2e"
    if normalized.startswith("tests/backend/"):
        return "backend-sqlite-compatible"
    return "generic"


def expand_block_specs_for_regression(block_specs: list[BlockSpec], regression_mode: str) -> list[BlockSpec]:
    if regression_mode == "light":
        return block_specs

    expanded: list[BlockSpec] = []
    seen_pairs: set[tuple[str, str]] = set()
    domain_tags = set()
    for block_spec in block_specs:
        for path in block_spec.paths:
            seen_pairs.add((block_spec.name, path))
            domain_tags.update(classify_domain_tags(path))
        base_metadata = dict(block_spec.path_metadata or {})
        for path in block_spec.paths:
            base_metadata.setdefault(path.replace("\\", "/"), {"origin": "primary", "origin_detail": "direct-target"})
        expanded.append(
            BlockSpec(
                name=block_spec.name,
                concurrency=block_spec.concurrency,
                paths=list(block_spec.paths),
                path_metadata=base_metadata,
            )
        )

    for tag in sorted(domain_tags):
        for extra_path in REGRESSION_EXPANSIONS.get(tag, {}).get(regression_mode, []):
            block_name = infer_block_name_from_path(extra_path)
            pair = (block_name, extra_path)
            if pair in seen_pairs:
                continue
            existing = next((spec for spec in expanded if spec.name == block_name), None)
            if existing is None:
                # Use a conservative default for newly expanded blocks.
                concurrency = 1 if block_name in ("backend-postgres-sensitive", "playwright-e2e") else 2
                expanded.append(
                    BlockSpec(
                        name=block_name,
                        concurrency=concurrency,
                        paths=[extra_path],
                        path_metadata={
                            extra_path: {
                                "origin": "regression",
                                "origin_detail": f"{regression_mode}-expansion:{tag}",
                            }
                        },
                    )
                )
            else:
                existing.paths.append(extra_path)
                if existing.path_metadata is None:
                    existing.path_metadata = {}
                existing.path_metadata[extra_path] = {
                    "origin": "regression",
                    "origin_detail": f"{regression_mode}-expansion:{tag}",
                }
            seen_pairs.add(pair)
    return expanded


def classify_block_tasks(block_specs: list[BlockSpec], postgres_base_port: int) -> tuple[list[Task], dict[str, int]]:
    tasks: list[Task] = []
    block_concurrency: dict[str, int] = {}
    port_cursor = postgres_base_port
    for block_spec in block_specs:
        block_concurrency[block_spec.name] = block_spec.concurrency
        block_tasks = classify_tasks(block_spec.paths, block_spec.name, port_cursor)
        metadata = block_spec.path_metadata or {}
        for task in block_tasks:
            task_meta = metadata.get(task.shard) or metadata.get(task.source_path or "")
            if task_meta:
                task.origin = task_meta.get("origin", task.origin)
                task.origin_detail = task_meta.get("origin_detail", task.origin_detail)
        tasks.extend(block_tasks)
        postgres_count = sum(1 for task in block_tasks if task.kind == "postgres")
        port_cursor += postgres_count
    return tasks, block_concurrency


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_console_report(progress_payload: dict[str, Any]) -> None:
    print("\n" + "=" * 100)
    payload = dict(progress_payload)
    payload["events_file_path"] = str(Path(str(progress_payload["run_dir"])) / "events.log")
    render_progress_snapshot(payload, str(progress_payload.get("run_id") or "n/a"))
    sys.stdout.flush()


def write_queue_snapshot(
    queue: list[Task],
    run_id: str,
    run_dir: Path,
    concurrency: int,
    regression_mode: str,
    block_concurrency: dict[str, int],
) -> None:
    write_json(
        QUEUE_PATH,
        {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "concurrency": concurrency,
            "regression_mode": regression_mode,
            "block_concurrency": block_concurrency,
            "queue_remaining": [asdict(task) for task in queue],
        },
    )


def append_event(events_path: Path, line: str) -> None:
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def update_current_run(run_id: str, run_dir: Path) -> None:
    write_json(
        CURRENT_RUN_PATH,
        {
            "run_id": run_id,
            "progress_file": str(run_dir / "progress.json"),
            "events_file": str(run_dir / "events.log"),
            "results_file": str(run_dir / "results.jsonl"),
            "run_config_file": str(run_dir / "run-config.json"),
            "mode": "supervisor",
        },
    )


def update_state(
    *,
    run_id: str,
    run_dir: Path,
    status: str,
    block: str,
    concurrency: int,
    regression_mode: str,
    total: int,
    completed: list[str],
    failed: list[str],
    block_summaries: dict[str, Any],
    block_concurrency: dict[str, int],
    error: dict[str, Any] | None = None,
) -> None:
    payload = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": status,
        "block": block,
        "concurrency": concurrency,
        "regression_mode": regression_mode,
        "block_concurrency": block_concurrency,
        "total": total,
        "completed_count": len(completed),
        "failed_count": len(failed),
        "completed": completed,
        "failed": failed,
        "blocks": block_summaries,
        "pid": os.getpid(),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    if error:
        payload["error"] = error
    write_json(STATE_PATH, payload)


def write_supervisor_error(run_dir: Path, exc: BaseException) -> dict[str, str]:
    error_payload = {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "traceback_file": str(run_dir / "supervisor-error.txt"),
    }
    traceback_text = "".join(traceback.format_exception(exc))
    (run_dir / "supervisor-error.txt").write_text(traceback_text, encoding="utf-8")
    return error_payload


def update_progress(
    *,
    run_dir: Path,
    block: str,
    concurrency: int,
    regression_mode: str,
    queue: list[Task],
    running: list[RunningTask],
    completed: list[str],
    failed: list[str],
    total: int,
    tasks: list[Task],
    block_concurrency: dict[str, int],
) -> None:
    task_index = {task.shard: task for task in tasks}
    block_names = sorted({task.block for task in tasks})
    block_summaries: dict[str, Any] = {}
    completed_set = set(completed)
    failed_set = set(failed)
    queued_counts: dict[str, int] = {}
    for queued in queue:
        queued_counts[queued.block] = queued_counts.get(queued.block, 0) + 1

    running_entries: list[dict[str, Any]] = []
    for running_task in running:
        running_entries.append(
            {
                "shard": running_task.task.shard,
                "display_name": running_task.task.shard,
                "source_path": running_task.task.source_path,
                "target": running_task.task.target or running_task.task.shard,
                "block": running_task.task.block,
                "kind": running_task.task.kind,
                "origin": running_task.task.origin,
                "origin_detail": running_task.task.origin_detail,
                "slot_label": running_task.task.shard,
                "started_at_epoch": running_task.started_at,
            }
        )

    for block_name in block_names:
        block_tasks = [task for task in tasks if task.block == block_name]
        block_completed = sum(1 for task in block_tasks if task.shard in completed_set)
        block_failed = sum(1 for task in block_tasks if task.shard in failed_set)
        block_running = [entry for entry in running_entries if entry["block"] == block_name]
        block_summaries[block_name] = {
            "name": block_name,
            "configured_concurrency": block_concurrency.get(block_name),
            "total": len(block_tasks),
            "completed_count": block_completed,
            "failed_count": block_failed,
            "running_count": len(block_running),
            "queue_remaining": queued_counts.get(block_name, 0),
            "running_slots": block_running,
            "origins": {
                "primary": sum(1 for task in block_tasks if task.origin == "primary"),
                "regression": sum(1 for task in block_tasks if task.origin == "regression"),
                "retry": sum(1 for task in block_tasks if task.origin == "retry"),
            },
        }

    primary_total = sum(1 for task in tasks if task.origin == "primary")
    regression_total = sum(1 for task in tasks if task.origin == "regression")
    retry_total = sum(1 for task in tasks if task.origin == "retry")

    write_json(
        run_dir / "progress.json",
        {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "run_id": run_dir.name,
            "block": block,
            "concurrency": concurrency,
            "regression_mode": regression_mode,
            "block_concurrency": block_concurrency,
            "queue_remaining": len(queue),
            "running": [task.task.shard for task in running],
            "running_slots": running_entries,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completed": completed,
            "failed": failed,
            "total": total,
            "passed_count": len(completed),
            "report": {
                "summary": {
                    "passed": len(completed),
                    "failed": len(failed),
                    "total": total,
                    "running": len(running),
                    "queued": len(queue),
                },
                "blocks": block_summaries,
                "origins": {
                    "primary_total": primary_total,
                    "regression_total": regression_total,
                    "retry_total": retry_total,
                },
            },
        },
    )


def ensure_clean_run_dir(run_dir: Path, replace_run_dir: bool) -> None:
    if not run_dir.exists():
        run_dir.mkdir(parents=True, exist_ok=True)
        return
    if replace_run_dir:
        shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return
    raise SystemExit(
        f"Run directory already exists: {run_dir}. Use a fresh run id or --replace-run-dir for an intentional rerun."
    )


def build_pg_worker_script(task: Task, run_dir: Path) -> Path:
    if task.port is None:
        raise ValueError(f"PostgreSQL task missing port: {task.shard}")
    db_name = f"courseeval_pytest_{task.port}"
    script_path = run_dir / "WAI-VALID-pg-worker.ps1"
    script_body = f"""$ErrorActionPreference = 'Stop'
$pythonExe = '{PYTHON_EXE}'
$postgresExe = '{POSTGRES_EXE}'
$psqlExe = '{PSQL_EXE}'
$initdbExe = '{INITDB_EXE}'
$dataDir = Join-Path '{run_dir}' 'data'
$pgOut = Join-Path '{run_dir}' 'postgres.out.log'
$pgErr = Join-Path '{run_dir}' 'postgres.err.log'
$initLog = Join-Path '{run_dir}' 'initdb.log'
$pytestLog = Join-Path '{run_dir}' 'WAI-VALID-worker-{safe_name(task.shard)}.log'
$dbName = '{db_name}'
$dbUser = 'courseeval_test'
$dbPass = 'courseeval_test'
$port = {task.port}
$pgProcess = $null
try {{
  & $initdbExe -D $dataDir -U postgres -A trust -E UTF8 --no-locale *>&1 | Tee-Object -FilePath $initLog
  if ($LASTEXITCODE -ne 0) {{ throw 'initdb failed' }}
  $pgProcess = Start-Process -FilePath $postgresExe -ArgumentList '-D', $dataDir, '-h', '127.0.0.1', '-p', "$port" -RedirectStandardOutput $pgOut -RedirectStandardError $pgErr -WindowStyle Hidden -PassThru
  $ready = $false
  for ($i = 0; $i -lt 120; $i++) {{
    Start-Sleep -Seconds 1
    try {{
      $result = & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -tAc "select 1;" 2>$null
      if ($LASTEXITCODE -eq 0 -and ($result | Out-String).Trim() -eq '1') {{ $ready = $true; break }}
    }} catch {{}}
  }}
  if (-not $ready) {{ throw 'postgres not ready' }}

  $roleExists = & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -tAc "select 1 from pg_roles where rolname = '$dbUser';"
  if (($roleExists | Out-String).Trim() -ne '1') {{
    & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE $dbUser LOGIN PASSWORD '$dbPass';"
    if ($LASTEXITCODE -ne 0) {{ throw 'create role failed' }}
  }} else {{
    & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE $dbUser WITH LOGIN PASSWORD '$dbPass';"
    if ($LASTEXITCODE -ne 0) {{ throw 'alter role failed' }}
  }}

  $dbExists = & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -tAc "select 1 from pg_database where datname = '$dbName';"
  if (($dbExists | Out-String).Trim() -eq '1') {{
    & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE $dbName;"
    if ($LASTEXITCODE -ne 0) {{ throw 'drop database failed' }}
  }}
  & $psqlExe -h 127.0.0.1 -p $port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $dbName OWNER $dbUser;"
  if ($LASTEXITCODE -ne 0) {{ throw 'create database failed' }}
  & $psqlExe -h 127.0.0.1 -p $port -U postgres -d $dbName -v ON_ERROR_STOP=1 -c "GRANT ALL ON SCHEMA public TO $dbUser;"
  if ($LASTEXITCODE -ne 0) {{ throw 'grant failed' }}

  $env:TEST_DATABASE_URL = "postgresql+psycopg2://${{dbUser}}:${{dbPass}}@127.0.0.1:${{port}}/${{dbName}}"
  & $pythonExe -m pytest '{task.shard}' -q *>&1 | Tee-Object -FilePath $pytestLog
  exit $LASTEXITCODE
}} finally {{
  if ($pgProcess -and -not $pgProcess.HasExited) {{ Stop-Process -Id $pgProcess.Id -Force }}
}}
"""
    script_path.write_text(script_body, encoding="utf-8")
    return script_path


def start_pytest_worker(task: Task, run_dir: Path) -> RunningTask:
    safe = safe_name(task.shard)
    log_path = run_dir / f"WAI-VALID-worker-{safe}.log"
    err_path = run_dir / f"WAI-VALID-worker-{safe}.err.log"
    out_fh = log_path.open("wb")
    err_fh = err_path.open("wb")
    proc = subprocess.Popen(
        [str(PYTHON_EXE), "-m", "pytest", task.target or task.shard, "-q"],
        cwd=str(REPO_ROOT),
        stdout=out_fh,
        stderr=err_fh,
    )
    return RunningTask(task=task, proc=proc, log_path=log_path, err_path=err_path, run_dir=None, started_at=time.time())


def start_postgres_worker(task: Task, run_dir: Path) -> RunningTask:
    safe = safe_name(task.shard)
    worker_dir = run_dir / f"WAI-VALID-pg-worker-{safe}"
    if worker_dir.exists():
        shutil.rmtree(worker_dir)
    worker_dir.mkdir(parents=True, exist_ok=True)
    script_path = build_pg_worker_script(task, worker_dir)
    out_path = worker_dir / "wrapper.out.log"
    err_path = worker_dir / "wrapper.err.log"
    out_fh = out_path.open("wb")
    err_fh = err_path.open("wb")
    proc = subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        cwd=str(REPO_ROOT),
        stdout=out_fh,
        stderr=err_fh,
    )
    return RunningTask(
        task=task,
        proc=proc,
        log_path=worker_dir / f"WAI-VALID-worker-{safe}.log",
        err_path=err_path,
        run_dir=worker_dir,
        started_at=time.time(),
    )


def start_playwright_worker(task: Task, run_dir: Path) -> RunningTask:
    if task.port is None or task.aux_port is None:
        raise ValueError(f"Playwright task missing ports: {task.shard}")
    safe = safe_name(task.shard)
    log_path = run_dir / f"WAI-VALID-worker-{safe}.log"
    err_path = run_dir / f"WAI-VALID-worker-{safe}.err.log"
    out_fh = log_path.open("wb")
    err_fh = err_path.open("wb")
    spec_name = Path(task.shard).name
    runner = REPO_ROOT / "apps" / "web" / "school" / "scripts" / "playwright-external-runner.cjs"
    proc = subprocess.Popen(
        [
            "node",
            str(runner),
            spec_name,
            "--project=chromium",
        ],
        cwd=str(REPO_ROOT / "apps" / "web" / "school"),
        env={
            **os.environ,
            "E2E_API_PORT": str(task.port),
            "E2E_UI_PORT": str(task.aux_port),
            "PLAYWRIGHT_USE_EXTERNAL_SERVERS": "true",
        },
        stdout=out_fh,
        stderr=err_fh,
    )
    return RunningTask(task=task, proc=proc, log_path=log_path, err_path=err_path, run_dir=None, started_at=time.time())


def start_task(task: Task, run_dir: Path) -> RunningTask:
    if task.kind == "postgres":
        return start_postgres_worker(task, run_dir)
    if task.kind == "playwright":
        return start_playwright_worker(task, run_dir)
    return start_pytest_worker(task, run_dir)


def append_result(results_path: Path, running_task: RunningTask, exit_code: int) -> None:
    payload = {
        "shard": running_task.task.shard,
        "kind": running_task.task.kind,
        "block": running_task.task.block,
        "port": running_task.task.port,
        "exit_code": exit_code,
        "log_path": str(running_task.log_path),
        "stderr_path": str(running_task.err_path),
        "run_dir": str(running_task.run_dir) if running_task.run_dir else None,
        "started_at_epoch": running_task.started_at,
        "ended_at_epoch": time.time(),
    }
    with results_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def classify_failure_type(result: dict[str, Any]) -> str:
    exit_code = int(result.get("exit_code") or 0)
    if exit_code == 0:
        return "passed"
    if exit_code == 3221225786:
        return "external-interrupt-control-c"

    candidate_paths = []
    for key in ("stderr_path", "log_path"):
        value = result.get(key)
        if value:
            candidate_paths.append(Path(str(value)))
    run_dir = result.get("run_dir")
    if run_dir:
        candidate_paths.extend(
            [
                Path(str(run_dir)) / "wrapper.err.log",
                Path(str(run_dir)) / "postgres.err.log",
                Path(str(run_dir)) / "initdb.log",
            ]
        )

    text_parts: list[str] = []
    for candidate in candidate_paths:
        try:
            if candidate.exists():
                text_parts.append(candidate.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    combined = "\n".join(text_parts)
    lowered = combined.lower()

    if "could not create restricted token" in lowered or "postgres not ready" in lowered or "initdb failed" in lowered:
        return "environment-postgres-bootstrap"
    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return "environment-python-deps"
    if "npm" in lowered and "not recognized" in lowered:
        return "environment-node-tooling"
    if "error: spawn eperm" in lowered or "spawn eperm" in lowered:
        return "environment-process-spawn"
    if "assertionerror" in lowered or "failed" in lowered or "traceback" in lowered:
        return "test-or-product-failure"
    return "unknown-failure"


def write_block_report(run_dir: Path, summary_payload: dict[str, Any]) -> None:
    results_path = run_dir / "results.jsonl"
    parsed_results: list[dict[str, Any]] = []
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload["failure_type"] = classify_failure_type(payload)
            parsed_results.append(payload)

    failure_counts: dict[str, int] = {}
    for result in parsed_results:
        failure_type = str(result.get("failure_type") or "unknown-failure")
        if failure_type == "passed":
            continue
        failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1

    report_payload = {
        "run_id": summary_payload.get("run_id"),
        "status": summary_payload.get("status"),
        "regression_mode": summary_payload.get("regression_mode"),
        "block_concurrency": summary_payload.get("block_concurrency"),
        "total": summary_payload.get("total"),
        "completed_count": summary_payload.get("completed_count"),
        "failed_count": summary_payload.get("failed_count"),
        "failure_type_counts": failure_counts,
        "results": parsed_results,
    }
    write_json(run_dir / "block-report.json", report_payload)

    lines = [
        f"run_id: {summary_payload.get('run_id')}",
        f"status: {summary_payload.get('status')}",
        f"regression_mode: {summary_payload.get('regression_mode')}",
        f"total: {summary_payload.get('total')}",
        f"passed: {summary_payload.get('completed_count')}",
        f"failed: {summary_payload.get('failed_count')}",
        "failure_types:",
    ]
    if failure_counts:
        for failure_type, count in sorted(failure_counts.items()):
            lines.append(f" - {failure_type}: {count}")
    else:
        lines.append(" - none")
    lines.append("failed_shards:")
    failed_results = [result for result in parsed_results if result.get("failure_type") != "passed"]
    if failed_results:
        for result in failed_results:
            lines.append(
                f" - {result.get('shard')} | {result.get('failure_type')} | exit={result.get('exit_code')}"
            )
    else:
        lines.append(" - none")
    (run_dir / "block-summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    ensure_python()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = ensure_prefixed_run_id(args.run_id)
    block_specs = expand_block_specs_for_regression(build_block_specs(args), args.regression_mode)
    tasks, block_concurrency = classify_block_tasks(block_specs, args.postgres_base_port)
    if not tasks:
        raise SystemExit("No tasks were classified from the provided paths.")
    block = tasks[0].block
    run_dir = LOG_ROOT / run_id
    ensure_clean_run_dir(run_dir, args.replace_run_dir)
    max_concurrency = max(block_concurrency.values())

    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    update_current_run(run_id, run_dir)
    write_json(
        run_dir / "run-config.json",
        {
            "run_id": run_id,
            "block": block,
            "concurrency": max_concurrency,
            "heartbeat_seconds": args.heartbeat_seconds,
            "regression_mode": args.regression_mode,
            "blocks": [
                {
                    "name": block_spec.name,
                    "concurrency": block_spec.concurrency,
                    "paths": block_spec.paths,
                }
                for block_spec in block_specs
            ],
            "block_concurrency": block_concurrency,
            "tasks": [asdict(task) for task in tasks],
        },
    )

    queue = list(tasks)
    running: list[RunningTask] = []
    completed: list[str] = []
    failed: list[str] = []
    events_path = run_dir / "events.log"
    results_path = run_dir / "results.jsonl"
    last_progress_write = 0.0

    update_state(
        run_id=run_id,
        run_dir=run_dir,
        status="running",
        block=block,
        concurrency=max_concurrency,
        regression_mode=args.regression_mode,
        total=len(tasks),
        completed=completed,
        failed=failed,
        block_summaries={},
        block_concurrency=block_concurrency,
    )
    write_queue_snapshot(queue, run_id, run_dir, max_concurrency, args.regression_mode, block_concurrency)
    progress_payload = update_progress(
        run_dir=run_dir,
        block=block,
        concurrency=max_concurrency,
        regression_mode=args.regression_mode,
        queue=queue,
        running=running,
        completed=completed,
        failed=failed,
        total=len(tasks),
        tasks=tasks,
        block_concurrency=block_concurrency,
    )
    if not args.no_console_report:
        render_console_report(
            {
                **json.loads((run_dir / "progress.json").read_text(encoding="utf-8")),
                "run_dir": str(run_dir),
            }
        )

    try:
        while queue or running:
            state_changed = False
            next_task_index: int | None = None
            for index, candidate in enumerate(queue):
                block_running_count = sum(1 for worker in running if worker.task.block == candidate.block)
                if block_running_count < block_concurrency.get(candidate.block, max_concurrency):
                    next_task_index = index
                    break
            while next_task_index is not None:
                task = queue.pop(next_task_index)
                worker = start_task(task, run_dir)
                running.append(worker)
                append_event(
                    events_path,
                    f"START {task.kind} {task.shard} block={task.block} origin={task.origin} detail={task.origin_detail} {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
                )
                write_queue_snapshot(queue, run_id, run_dir, max_concurrency, args.regression_mode, block_concurrency)
                state_changed = True
                next_task_index = None
                for index, candidate in enumerate(queue):
                    block_running_count = sum(1 for worker in running if worker.task.block == candidate.block)
                    if block_running_count < block_concurrency.get(candidate.block, max_concurrency):
                        next_task_index = index
                        break

            next_running: list[RunningTask] = []
            for worker in running:
                exit_code = worker.proc.poll()
                if exit_code is None:
                    next_running.append(worker)
                    continue
                if exit_code == 0:
                    completed.append(worker.task.shard)
                else:
                    failed.append(worker.task.shard)
                append_result(results_path, worker, exit_code)
                append_event(
                    events_path,
                    f"END {worker.task.kind} {worker.task.shard} block={worker.task.block} origin={worker.task.origin} exit={exit_code} {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
                )
                write_queue_snapshot(queue, run_id, run_dir, max_concurrency, args.regression_mode, block_concurrency)
                state_changed = True
            running = next_running

            active_block = running[0].task.block if running else (queue[0].block if queue else block)
            now = time.time()
            if state_changed or now - last_progress_write >= args.heartbeat_seconds:
                update_progress(
                    run_dir=run_dir,
                    block=active_block,
                    concurrency=max_concurrency,
                    regression_mode=args.regression_mode,
                    queue=queue,
                    running=running,
                    completed=completed,
                    failed=failed,
                    total=len(tasks),
                    tasks=tasks,
                    block_concurrency=block_concurrency,
                )
                block_summaries = (json.loads((run_dir / "progress.json").read_text(encoding="utf-8")).get("report") or {}).get("blocks") or {}
                update_state(
                    run_id=run_id,
                    run_dir=run_dir,
                    status="running",
                    block=active_block,
                    concurrency=max_concurrency,
                    regression_mode=args.regression_mode,
                    total=len(tasks),
                    completed=completed,
                    failed=failed,
                    block_summaries=block_summaries,
                    block_concurrency=block_concurrency,
                )
                if not args.no_console_report:
                    render_console_report(
                        {
                            **json.loads((run_dir / "progress.json").read_text(encoding="utf-8")),
                            "run_dir": str(run_dir),
                        }
                    )
                last_progress_write = now
            time.sleep(1)
    except Exception as exc:
        error_payload = write_supervisor_error(run_dir, exc)
        append_event(
            events_path,
            f"SUPERVISOR_ERROR type={error_payload['type']} message={error_payload['message']} {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
        )
        update_state(
            run_id=run_id,
            run_dir=run_dir,
            status="supervisor_error",
            block=block,
            concurrency=max_concurrency,
            regression_mode=args.regression_mode,
            total=len(tasks),
            completed=completed,
            failed=failed,
            block_summaries={},
            block_concurrency=block_concurrency,
            error=error_payload,
        )
        raise
    finally:
        if PID_PATH.exists():
            PID_PATH.unlink()

    summary_status = "passed" if not failed else "failed"
    summary_payload = {
        "run_id": run_id,
        "status": summary_status,
        "block": block,
        "concurrency": max_concurrency,
        "regression_mode": args.regression_mode,
        "block_concurrency": block_concurrency,
        "total": len(tasks),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "completed_shards": completed,
        "failed_shards": failed,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    write_json(run_dir / "summary.json", summary_payload)
    write_block_report(run_dir, summary_payload)
    update_progress(
        run_dir=run_dir,
        block=block,
        concurrency=max_concurrency,
        regression_mode=args.regression_mode,
        queue=queue,
        running=running,
        completed=completed,
        failed=failed,
        total=len(tasks),
        tasks=tasks,
        block_concurrency=block_concurrency,
    )
    block_summaries = (json.loads((run_dir / "progress.json").read_text(encoding="utf-8")).get("report") or {}).get("blocks") or {}
    update_state(
        run_id=run_id,
        run_dir=run_dir,
        status=summary_status,
        block=block,
        concurrency=max_concurrency,
        regression_mode=args.regression_mode,
        total=len(tasks),
        completed=completed,
        failed=failed,
        block_summaries=block_summaries,
        block_concurrency=block_concurrency,
    )
    if not args.no_console_report:
        render_console_report(
            {
                **json.loads((run_dir / "progress.json").read_text(encoding="utf-8")),
                "run_dir": str(run_dir),
            }
        )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

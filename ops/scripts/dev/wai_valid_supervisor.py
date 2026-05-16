from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


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


@dataclass
class RunningTask:
    task: Task
    proc: subprocess.Popen[Any]
    log_path: Path
    err_path: Path
    run_dir: Path | None
    started_at: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Pytest shard paths or directories to supervise.")
    parser.add_argument("--run-id", required=True, help="Logical run id. 'WAI-VALID-' is added if missing.")
    parser.add_argument("--concurrency", type=int, required=True, help="Maximum concurrent shards for this run.")
    parser.add_argument(
        "--block",
        default="auto",
        help="Optional logical block name for progress reporting. Defaults to auto classification.",
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
    return parser.parse_args()


def ensure_prefixed_run_id(run_id: str) -> str:
    return run_id if run_id.startswith("WAI-VALID-") else f"WAI-VALID-{run_id}"


def ensure_python() -> None:
    if not PYTHON_EXE.exists():
        raise SystemExit(f"Missing repository venv interpreter: {PYTHON_EXE}")


def safe_name(shard: str) -> str:
    out = shard
    for ch in "\\/:. ":
        out = out.replace(ch, "_")
    return out


def classify_tasks(paths: list[str], block_name: str, postgres_base_port: int) -> list[Task]:
    tasks: list[Task] = []
    pg_index = 0
    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        if path.startswith("tests/postgres/"):
            tasks.append(
                Task(
                    shard=path,
                    kind="postgres",
                    block=block_name if block_name != "auto" else "backend-postgres-sensitive",
                    port=postgres_base_port + pg_index,
                )
            )
            pg_index += 1
            continue
        if path.startswith("tests/behavior/"):
            tasks.append(
                Task(
                    shard=path,
                    kind="pytest",
                    block=block_name if block_name != "auto" else "behavior",
                )
            )
            continue
        if path.startswith("tests/backend/"):
            tasks.append(
                Task(
                    shard=path,
                    kind="pytest",
                    block=block_name if block_name != "auto" else "backend-sqlite-compatible",
                )
            )
            continue
        tasks.append(
            Task(
                shard=path,
                kind="pytest",
                block=block_name if block_name != "auto" else "generic",
            )
        )
    return tasks


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_queue_snapshot(queue: list[Task], run_id: str, run_dir: Path, concurrency: int) -> None:
    write_json(
        QUEUE_PATH,
        {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "concurrency": concurrency,
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
    total: int,
    completed: list[str],
    failed: list[str],
) -> None:
    write_json(
        STATE_PATH,
        {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": status,
            "block": block,
            "concurrency": concurrency,
            "total": total,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completed": completed,
            "failed": failed,
            "pid": os.getpid(),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        },
    )


def update_progress(
    *,
    run_dir: Path,
    block: str,
    concurrency: int,
    queue: list[Task],
    running: list[RunningTask],
    completed: list[str],
    failed: list[str],
    total: int,
) -> None:
    write_json(
        run_dir / "progress.json",
        {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "run_id": run_dir.name,
            "block": block,
            "concurrency": concurrency,
            "queue_remaining": len(queue),
            "running": [task.task.shard for task in running],
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completed": completed,
            "failed": failed,
            "total": total,
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
        [str(PYTHON_EXE), "-m", "pytest", task.shard, "-q"],
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


def start_task(task: Task, run_dir: Path) -> RunningTask:
    if task.kind == "postgres":
        return start_postgres_worker(task, run_dir)
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


def main() -> int:
    args = parse_args()
    ensure_python()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = ensure_prefixed_run_id(args.run_id)
    tasks = classify_tasks(args.paths, args.block, args.postgres_base_port)
    if not tasks:
        raise SystemExit("No tasks were classified from the provided paths.")
    block = args.block if args.block != "auto" else tasks[0].block
    run_dir = LOG_ROOT / run_id
    ensure_clean_run_dir(run_dir, args.replace_run_dir)

    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    update_current_run(run_id, run_dir)
    write_json(
        run_dir / "run-config.json",
        {
            "run_id": run_id,
            "block": block,
            "concurrency": args.concurrency,
            "heartbeat_seconds": args.heartbeat_seconds,
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
        concurrency=args.concurrency,
        total=len(tasks),
        completed=completed,
        failed=failed,
    )
    write_queue_snapshot(queue, run_id, run_dir, args.concurrency)
    update_progress(
        run_dir=run_dir,
        block=block,
        concurrency=args.concurrency,
        queue=queue,
        running=running,
        completed=completed,
        failed=failed,
        total=len(tasks),
    )

    try:
        while queue or running:
            state_changed = False
            while queue and len(running) < args.concurrency:
                task = queue.pop(0)
                worker = start_task(task, run_dir)
                running.append(worker)
                append_event(
                    events_path,
                    f"START {task.kind} {task.shard} {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
                )
                write_queue_snapshot(queue, run_id, run_dir, args.concurrency)
                state_changed = True

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
                    f"END {worker.task.kind} {worker.task.shard} exit={exit_code} {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
                )
                write_queue_snapshot(queue, run_id, run_dir, args.concurrency)
                state_changed = True
            running = next_running

            now = time.time()
            if state_changed or now - last_progress_write >= args.heartbeat_seconds:
                update_progress(
                    run_dir=run_dir,
                    block=block,
                    concurrency=args.concurrency,
                    queue=queue,
                    running=running,
                    completed=completed,
                    failed=failed,
                    total=len(tasks),
                )
                update_state(
                    run_id=run_id,
                    run_dir=run_dir,
                    status="running",
                    block=block,
                    concurrency=args.concurrency,
                    total=len(tasks),
                    completed=completed,
                    failed=failed,
                )
                last_progress_write = now
            time.sleep(1)
    except Exception:
        update_state(
            run_id=run_id,
            run_dir=run_dir,
            status="supervisor_error",
            block=block,
            concurrency=args.concurrency,
            total=len(tasks),
            completed=completed,
            failed=failed,
        )
        raise
    finally:
        if PID_PATH.exists():
            PID_PATH.unlink()

    summary_status = "passed" if not failed else "failed"
    write_json(
        run_dir / "summary.json",
        {
            "run_id": run_id,
            "status": summary_status,
            "block": block,
            "concurrency": args.concurrency,
            "total": len(tasks),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completed_shards": completed,
            "failed_shards": failed,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        },
    )
    update_progress(
        run_dir=run_dir,
        block=block,
        concurrency=args.concurrency,
        queue=queue,
        running=running,
        completed=completed,
        failed=failed,
        total=len(tasks),
    )
    update_state(
        run_id=run_id,
        run_dir=run_dir,
        status=summary_status,
        block=block,
        concurrency=args.concurrency,
        total=len(tasks),
        completed=completed,
        failed=failed,
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

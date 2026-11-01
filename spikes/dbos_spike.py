"""Spike: DBOS durability, queues, schedules. Run via spikes/run_dbos_spike.sh."""

import os
import sys
import threading
import time
from pathlib import Path

from dbos import DBOS, DBOSConfig, SetEnqueueOptions, SetWorkflowID
from dbos._queue import QueueRateLimit

URL = os.environ.get(
    "SPIKE_DB", "postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply_spike"
)
OUT = Path(os.environ.get("SPIKE_OUT", "/tmp/dbos_spike"))
OUT.mkdir(exist_ok=True)

config: DBOSConfig = {"name": "kame-spike", "system_database_url": URL}
DBOS(config=config)


def mark(name: str) -> None:
    with (OUT / f"{name}.log").open("a") as f:
        f.write(f"{time.time():.3f}\n")


@DBOS.step()
def step_one() -> str:
    mark("step1")
    return "one"


@DBOS.step()
def step_three(msg: str) -> str:
    mark("step3")
    return f"done:{msg}"


@DBOS.workflow()
def durable_wf() -> str:
    step_one()
    msg = DBOS.recv("go", timeout_seconds=600)  # step 2: wait for a human
    assert msg is not None
    return step_three(msg)


# --- queue: per-key concurrency 1 + rate limit ---
keyed = limited = None  # registered after launch (queues are persisted in the system DB)
active: dict[str, int] = {}
max_active: dict[str, int] = {}
lock = threading.Lock()


@DBOS.step()
def keyed_task(key: str) -> None:
    with lock:
        active[key] = active.get(key, 0) + 1
        max_active[key] = max(max_active.get(key, 0), active[key])
    time.sleep(0.6)
    with lock:
        active[key] -= 1


@DBOS.step()
def stamp() -> float:
    return time.time()


@DBOS.workflow()
def keyed_wf(key: str) -> None:
    keyed_task(key)


@DBOS.workflow()
def limited_wf() -> float:
    return stamp()


# --- schedule ---
@DBOS.workflow()
def tick(scheduled_time: object, context: object) -> None:
    mark("tick")


def main() -> None:
    mode = sys.argv[1]
    if mode == "start":
        DBOS.launch()
        with SetWorkflowID("wf-durable"):
            DBOS.start_workflow(durable_wf)
        time.sleep(300)  # killed externally while waiting in recv
    elif mode == "resume":
        DBOS.launch()  # recovers pending workflows
        time.sleep(2)
        DBOS.send("wf-durable", "approved", "go")
        result = DBOS.retrieve_workflow("wf-durable").get_result()
        s1 = (OUT / "step1.log").read_text().splitlines()
        s3 = (OUT / "step3.log").read_text().splitlines()
        print(f"result={result} step1_runs={len(s1)} step3_runs={len(s3)}")
        assert result == "done:approved" and len(s1) == 1 and len(s3) == 1
        print("DURABILITY OK")
    elif mode == "queues":
        global keyed, limited
        DBOS.launch()
        keyed = DBOS.register_queue("keyed", global_concurrency=4, partition_concurrency=1)
        limited = DBOS.register_queue("limited", limiter=QueueRateLimit(limit=3, period=2.0))
        handles = []
        for key in ("a", "b"):
            for _ in range(3):
                with SetEnqueueOptions(queue_partition_key=key):  # type: ignore[call-arg]
                    handles.append(keyed.enqueue(keyed_wf, key))
        t0 = time.time()
        for h in handles:
            h.get_result()
        print(f"keyed: max concurrent per key={max_active} total_time={time.time() - t0:.1f}s")
        t0 = time.time()
        hs = [limited.enqueue(limited_wf) for _ in range(6)]
        starts = sorted(h.get_result() for h in hs)
        rel = [round(s - t0, 1) for s in starts]
        print(f"limited(3 per 2s): start offsets={rel}")
        assert all(v == 1 for v in max_active.values()), max_active
        assert rel[3] - rel[2] >= 1.0, rel
        print("QUEUES OK")
    elif mode == "cron":
        DBOS.launch()
        try:
            DBOS.delete_schedule("spike-tick")
        except Exception:
            pass
        DBOS.create_schedule(schedule_name="spike-tick", workflow_fn=tick, schedule="* * * * * *")
        time.sleep(5.5)
        DBOS.delete_schedule("spike-tick")
        ticks = len((OUT / "tick.log").read_text().splitlines())
        print(f"ticks in 5.5s={ticks}")
        assert 3 <= ticks <= 7
        print("CRON OK")
    DBOS.destroy()


if __name__ == "__main__":
    main()

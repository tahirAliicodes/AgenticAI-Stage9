# Stage9/tracer/storage.py

import json
from pathlib import Path
from datetime import datetime
from models1.trace_models import Trace


TRACES_DIR = Path("traces")  # Stage9/traces/ folder, auto-created


def save_trace(trace: Trace):
    """Save a finished trace to disk as JSON."""
    TRACES_DIR.mkdir(exist_ok=True)

    filename = TRACES_DIR / f"{trace.trace_id}.json"
    with open(filename, "w") as f:
        json.dump(trace.model_dump(mode="json"), f, indent=2, default=str)

    print(f"[storage] 💾 saved trace {trace.trace_id}")


def load_all_traces() -> list[Trace]:
    """Load every saved trace from disk."""
    if not TRACES_DIR.exists():
        return []

    traces = []
    for file in sorted(TRACES_DIR.glob("*.json"), reverse=True):
        with open(file) as f:
            data = json.load(f)
            traces.append(Trace(**data))

    print(f"[storage] 📂 loaded {len(traces)} traces")
    return traces


def load_trace(trace_id: str) -> Trace | None:
    """Load one specific trace by ID."""
    file = TRACES_DIR / f"{trace_id}.json"
    if not file.exists():
        return None

    with open(file) as f:
        return Trace(**json.load(f))
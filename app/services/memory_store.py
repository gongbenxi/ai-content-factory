"""In-memory fallback store for local development without PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from typing import Any

RUNS: dict[str, dict[str, Any]] = {}
EVENTS: dict[str, list[dict[str, Any]]] = {}
STYLES: dict[str, dict[str, Any]] = {}


def upsert_run(run_id: str, **fields: Any) -> dict[str, Any]:
    run = RUNS.setdefault(
        run_id,
        {
            "id": run_id,
            "status": "drafting",
            "created_at": datetime.utcnow().isoformat(),
        },
    )
    run.update(fields)
    run["updated_at"] = datetime.utcnow().isoformat()
    return run


def append_event(run_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    rows = EVENTS.setdefault(run_id, [])
    row = {
        "id": len(rows) + 1,
        "event": event_type,
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
    }
    rows.append(row)
    return row

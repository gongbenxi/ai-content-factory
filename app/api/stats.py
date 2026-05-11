"""Stats API — Dashboard 统计"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


def _compute_from_memory() -> dict:
    """从 memory_store 的 RUNS 字典计算 dashboard 统计"""
    from app.services.memory_store import RUNS

    today = datetime.utcnow().date()
    today_count = 0
    done_count = 0
    total_cost = 0

    for run in RUNS.values():
        # 统计今日 runs
        created = run.get("created_at", "")
        if created:
            try:
                run_date = datetime.fromisoformat(created).date()
                if run_date == today:
                    today_count += 1
            except (ValueError, TypeError):
                pass

        status = run.get("status", "")
        if status in ("done", "completed"):
            done_count += 1

        total_cost += run.get("cost_cents", 0)

    total_count = len(RUNS)
    pass_rate = round(done_count / total_count, 2) if total_count > 0 else 0.0

    return {
        "today_runs": today_count,
        "completed_runs": done_count,
        "total_cost_cents": total_cost,
        "pass_rate": pass_rate,
    }


@router.get("/dashboard")
async def dashboard():
    """Dashboard KPI 数据"""
    try:
        from sqlalchemy import select, func, cast, Date
        from app.db.session import get_session
        from app.db.models import Run

        today = datetime.utcnow().date()
        async with get_session() as session:
            total = await session.execute(select(func.count(Run.id)))
            total_count = total.scalar() or 0

            today_q = await session.execute(
                select(func.count(Run.id)).where(cast(Run.created_at, Date) == today)
            )
            today_count = today_q.scalar() or 0

            done_q = await session.execute(
                select(func.count(Run.id)).where(Run.status == "done")
            )
            done_count = done_q.scalar() or 0

            cost_q = await session.execute(select(func.coalesce(func.sum(Run.cost_cents), 0)))
            total_cost = cost_q.scalar() or 0

        pass_rate = round(done_count / total_count, 2) if total_count > 0 else 0.0
        return {
            "today_runs": today_count,
            "completed_runs": done_count,
            "total_cost_cents": total_cost,
            "pass_rate": pass_rate,
        }
    except Exception:
        result = _compute_from_memory()
        result["_source"] = "memory"
        return result


def _cost_from_memory() -> dict:
    """从 memory_store 的 RUNS 计算成本趋势"""
    from app.services.memory_store import RUNS

    by_agent: dict[str, dict] = {}
    by_date: dict[str, int] = {}

    for run in RUNS.values():
        usage = run.get("usage_by_agent", {})
        for agent, info in usage.items():
            if agent not in by_agent:
                by_agent[agent] = {"cost_cents": 0, "input_tokens": 0, "output_tokens": 0}
            by_agent[agent]["cost_cents"] += info.get("cost_cents", 0)
            by_agent[agent]["input_tokens"] += info.get("input_tokens", 0)
            by_agent[agent]["output_tokens"] += info.get("output_tokens", 0)

        created = run.get("created_at", "")
        if created:
            try:
                date_str = str(datetime.fromisoformat(created).date())
                by_date[date_str] = by_date.get(date_str, 0) + run.get("cost_cents", 0)
            except (ValueError, TypeError):
                pass

    return {"cost_by_agent": by_agent, "cost_by_date": dict(sorted(by_date.items()))}


@router.get("/cost")
async def cost_trend():
    """Per-agent 成本趋势"""
    try:
        from sqlalchemy import select, func, cast, Date
        from app.db.session import get_session
        from app.db.models import TokenUsage

        async with get_session() as session:
            agent_q = await session.execute(
                select(
                    TokenUsage.agent,
                    func.sum(TokenUsage.cost_cents).label("cost"),
                    func.sum(TokenUsage.input_tokens).label("input_tokens"),
                    func.sum(TokenUsage.output_tokens).label("output_tokens"),
                ).group_by(TokenUsage.agent)
            )
            by_agent = {
                row.agent: {
                    "cost_cents": row.cost or 0,
                    "input_tokens": row.input_tokens or 0,
                    "output_tokens": row.output_tokens or 0,
                }
                for row in agent_q
            }

            date_q = await session.execute(
                select(
                    cast(TokenUsage.created_at, Date).label("date"),
                    func.sum(TokenUsage.cost_cents).label("cost"),
                ).group_by("date").order_by("date").limit(30)
            )
            by_date = {str(row.date): row.cost or 0 for row in date_q}

        return {"cost_by_agent": by_agent, "cost_by_date": by_date}
    except Exception:
        result = _cost_from_memory()
        result["_source"] = "memory"
        return result

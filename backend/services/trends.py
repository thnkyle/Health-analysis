from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import DataType, HealthRecord, TrendPoint, TrendResponse

GRANULARITY_MAP = {
    "daily": "D",
    "weekly": "W",
    "monthly": "ME",
}


def _period_key(dt: datetime, granularity: str) -> str:
    """Return a string key representing the period a datetime falls into."""
    if granularity == "daily":
        return str(dt.date())
    elif granularity == "weekly":
        # Start of ISO week (Monday)
        start = dt.date() - timedelta(days=dt.weekday())
        return str(start)
    else:  # monthly
        return str(dt.date().replace(day=1))


def compute_trends(
    db: Session, user_id: str, data_type: DataType, granularity: str
) -> TrendResponse:
    records = (
        db.query(HealthRecord)
        .filter(HealthRecord.user_id == user_id, HealthRecord.data_type == data_type)
        .order_by(HealthRecord.recorded_at)
        .all()
    )

    if not records:
        return TrendResponse(data_type=data_type.value, granularity=granularity, trends=[])

    # Group values by period
    buckets: dict[str, list[float]] = {}
    for r in records:
        recorded = r.recorded_at if isinstance(r.recorded_at, datetime) else datetime.fromisoformat(str(r.recorded_at))
        key = _period_key(recorded, granularity)
        buckets.setdefault(key, []).append(r.value)

    trends = []
    for period in sorted(buckets):
        values = buckets[period]
        trends.append(
            TrendPoint(
                period=period,
                avg=round(sum(values) / len(values), 2),
                min=round(min(values), 2),
                max=round(max(values), 2),
                count=len(values),
            )
        )

    return TrendResponse(
        data_type=data_type.value, granularity=granularity, trends=trends
    )

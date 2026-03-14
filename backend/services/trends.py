import pandas as pd
from sqlalchemy.orm import Session

from models import DataType, HealthRecord, TrendPoint, TrendResponse

GRANULARITY_MAP = {
    "daily": "D",
    "weekly": "W",
    "monthly": "ME",
}


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

    df = pd.DataFrame(
        [{"recorded_at": r.recorded_at, "value": r.value} for r in records]
    )
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    df = df.set_index("recorded_at")

    freq = GRANULARITY_MAP[granularity]
    grouped = df["value"].resample(freq)

    trends = []
    for period, group in grouped:
        if group.empty:
            continue
        trends.append(
            TrendPoint(
                period=str(period.date()),
                avg=round(group.mean(), 2),
                min=round(group.min(), 2),
                max=round(group.max(), 2),
                count=len(group),
            )
        )

    return TrendResponse(
        data_type=data_type.value, granularity=granularity, trends=trends
    )

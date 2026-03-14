import math
from sqlalchemy.orm import Session

from models import Anomaly, AnomalyResponse, DataType, HealthRecord


def detect_anomalies(
    db: Session,
    user_id: str,
    data_type: DataType | None,
    threshold: float,
) -> AnomalyResponse:
    query = db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
    if data_type:
        query = query.filter(HealthRecord.data_type == data_type)

    records = query.order_by(HealthRecord.recorded_at).all()

    if len(records) < 3:
        return AnomalyResponse(anomalies=[], total=0)

    # Group by data_type and detect anomalies within each group
    grouped: dict[str, list[HealthRecord]] = {}
    for r in records:
        grouped.setdefault(r.data_type.value, []).append(r)

    anomalies = []
    for dt, group in grouped.items():
        values = [r.value for r in group]
        n = len(values)
        mean = sum(values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / n)

        if std == 0:
            continue

        for r in group:
            z = abs((r.value - mean) / std)
            if z > threshold:
                anomalies.append(
                    Anomaly(
                        record_id=r.id,
                        data_type=dt,
                        value=r.value,
                        recorded_at=r.recorded_at,
                        z_score=round(z, 2),
                        message=f"Value {r.value} is {round(z, 1)} std devs from mean ({round(mean, 1)})",
                    )
                )

    anomalies.sort(key=lambda a: a.z_score, reverse=True)
    return AnomalyResponse(anomalies=anomalies, total=len(anomalies))

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import (
    DataType,
    HealthRecord,
    HealthRecordResponse,
    SyncRequest,
    SyncResponse,
)

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
def sync_records(request: SyncRequest, db: Session = Depends(get_db)):
    records = []
    for r in request.records:
        record = HealthRecord(
            user_id=r.user_id,
            data_type=r.data_type,
            value=r.value,
            unit=r.unit,
            recorded_at=r.recorded_at,
            metadata_json=r.metadata_json,
        )
        records.append(record)

    db.add_all(records)
    db.commit()
    return SyncResponse(inserted=len(records), message="ok")


@router.get("/records", response_model=list[HealthRecordResponse])
def get_records(
    user_id: str = Query(...),
    data_type: DataType | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(HealthRecord).filter(HealthRecord.user_id == user_id)

    if data_type:
        query = query.filter(HealthRecord.data_type == data_type)
    if start:
        query = query.filter(HealthRecord.recorded_at >= start)
    if end:
        query = query.filter(HealthRecord.recorded_at <= end)

    return query.order_by(HealthRecord.recorded_at.desc()).limit(limit).all()

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import User, get_current_user
from database import get_db
from models import (
    DataType,
    HealthRecord,
    HealthRecordResponse,
    SyncRequest,
    SyncResponse,
)
from validation import validate_records

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
def sync_records(
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_records(request.records)

    records = []
    for r in request.records:
        record = HealthRecord(
            user_id=current_user.username,
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
    data_type: DataType | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(HealthRecord).filter(HealthRecord.user_id == current_user.username)

    if data_type:
        query = query.filter(HealthRecord.data_type == data_type)
    if start:
        query = query.filter(HealthRecord.recorded_at >= start)
    if end:
        query = query.filter(HealthRecord.recorded_at <= end)

    return query.order_by(HealthRecord.recorded_at.desc()).limit(limit).all()

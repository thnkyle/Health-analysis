from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import AnomalyResponse, DataType, TrendResponse
from services.anomaly import detect_anomalies
from services.trends import compute_trends

router = APIRouter()


@router.get("/trends/{data_type}", response_model=TrendResponse)
def get_trends(
    data_type: DataType,
    user_id: str = Query(...),
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
):
    return compute_trends(db, user_id, data_type, granularity)


@router.get("/anomalies", response_model=AnomalyResponse)
def get_anomalies(
    user_id: str = Query(...),
    data_type: DataType | None = Query(None),
    threshold: float = Query(2.0, description="Z-score threshold"),
    db: Session = Depends(get_db),
):
    return detect_anomalies(db, user_id, data_type, threshold)

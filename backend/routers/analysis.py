from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import User, get_current_user
from database import get_db
from models import AnomalyResponse, DataType, TrendResponse
from services.anomaly import detect_anomalies
from services.trends import compute_trends

router = APIRouter()


@router.get("/trends/{data_type}", response_model=TrendResponse)
def get_trends(
    data_type: DataType,
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_trends(db, current_user.username, data_type, granularity)


@router.get("/anomalies", response_model=AnomalyResponse)
def get_anomalies(
    data_type: DataType | None = Query(None),
    threshold: float = Query(2.0, description="Z-score threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return detect_anomalies(db, current_user.username, data_type, threshold)

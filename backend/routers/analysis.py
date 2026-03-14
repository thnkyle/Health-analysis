from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import User, get_current_user
from database import get_db
from models import AIAnomalyResponse, AIHealthAnalysis, AnomalyResponse, DataType, TrendResponse
from services.anomaly import detect_anomalies
from services.ai_analysis import analyze_health_ai, detect_anomalies_ai
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


@router.get("/ai/insights", response_model=AIHealthAnalysis)
def get_ai_insights(
    data_type: DataType | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered health insights using Claude."""
    return analyze_health_ai(db, current_user.username, data_type)


@router.get("/ai/anomalies", response_model=AIAnomalyResponse)
def get_ai_anomalies(
    data_type: DataType | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered anomaly detection using Claude."""
    return detect_anomalies_ai(db, current_user.username, data_type)

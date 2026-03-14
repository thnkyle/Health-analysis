import enum
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class DataType(str, enum.Enum):
    steps = "steps"
    distance = "distance"
    calories = "calories"
    exercise = "exercise"
    heart_rate = "heart_rate"
    blood_pressure_systolic = "blood_pressure_systolic"
    blood_pressure_diastolic = "blood_pressure_diastolic"
    body_temperature = "body_temperature"
    weight = "weight"
    sleep = "sleep"
    nutrition = "nutrition"


# SQLAlchemy model
class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    data_type = Column(Enum(DataType), index=True, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_user_type", "user_id", "data_type"),
        Index("ix_user_recorded", "user_id", "recorded_at"),
        Index("ix_user_type_recorded", "user_id", "data_type", "recorded_at"),
    )


# Pydantic schemas
class HealthRecordCreate(BaseModel):
    data_type: DataType
    value: float
    unit: str
    recorded_at: datetime
    metadata_json: str = "{}"


class HealthRecordResponse(BaseModel):
    id: int
    user_id: str
    data_type: DataType
    value: float
    unit: str
    recorded_at: datetime
    metadata_json: str

    class Config:
        orm_mode = True


class SyncRequest(BaseModel):
    records: list[HealthRecordCreate]


class SyncResponse(BaseModel):
    inserted: int
    message: str


class TrendPoint(BaseModel):
    period: str
    avg: float
    min: float
    max: float
    count: int


class TrendResponse(BaseModel):
    data_type: str
    granularity: str
    trends: list[TrendPoint]


class Anomaly(BaseModel):
    record_id: int
    data_type: str
    value: float
    recorded_at: datetime
    z_score: float
    message: str


class AnomalyResponse(BaseModel):
    anomalies: list[Anomaly]
    total: int

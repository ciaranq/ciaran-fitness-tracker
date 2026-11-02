from datetime import datetime
from pydantic import BaseModel, Field

class BloodPressureReading(BaseModel):
    timestamp: datetime
    systolic: int = Field(..., ge=70, le=220)
    diastolic: int = Field(..., ge=40, le=140)
    pulse: int = Field(..., ge=30, le=220)

class SpirometryReading(BaseModel):
    timestamp: datetime
    peak_flow_l_min: int = Field(..., ge=100, le=900)
    notes: str | None = None

class ActivitySummary(BaseModel):
    activity_id: str
    start_time: datetime
    activity_type: str
    duration_seconds: float
    avg_heart_rate: int | None = None
    time_in_zone_2_seconds: float | None = None

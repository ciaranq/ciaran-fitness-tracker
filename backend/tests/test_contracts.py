from datetime import datetime
import pytest
from ingestion.contracts import BloodPressureReading, SpirometryReading, ActivitySummary

def test_blood_pressure():
    r = BloodPressureReading(timestamp=datetime.now(), systolic=118, diastolic=76, pulse=58)
    assert r.systolic == 118
    with pytest.raises(ValueError):
        BloodPressureReading(timestamp=datetime.now(), systolic=300, diastolic=76, pulse=58)

def test_spirometry():
    s = SpirometryReading(timestamp=datetime.now(), peak_flow_l_min=520)
    assert s.peak_flow_l_min == 520

def test_activity():
    a = ActivitySummary(activity_id="test_1", start_time=datetime.now(), activity_type="elliptical", duration_seconds=1800.0)
    assert a.activity_type == "elliptical"

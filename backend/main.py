from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ciaran Fitness Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "healthy", "engine": "FastAPI + UV (Python 3.12)"}

@app.get("/api/v1/baseline/summary")
def baseline_summary():
    return {
        "resting_heart_rate": 58,
        "blood_pressure": {"systolic": 118, "diastolic": 76},
        "peak_expiratory_flow_l_min": 520,
        "phase": "Base Conditioning (Month 1)"
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.plan import router as plan_router

app = FastAPI(title="Ciaran Fitness Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan_router)


@app.get("/api/health")
def health():
    return {"status": "healthy", "engine": "FastAPI + UV (Python 3.13+)"}

from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers import analysis, ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Health Analysis API",
    description="Backend for Health Connect data analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

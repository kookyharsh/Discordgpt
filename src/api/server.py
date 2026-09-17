from fastapi import FastAPI, Response, status
from sqlalchemy import text

from src.database.session import AsyncSessionLocal

app = FastAPI(title="Discord Agent Py API", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready(response: Response):
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_533_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": str(e)}


@app.get("/metrics")
async def metrics():
    import os

    import psutil

    process = psutil.Process(os.getpid()) if hasattr(psutil, "Process") else None
    return {
        "memory_mb": process.memory_info().rss / 1024 / 1024 if process else 0,
        "status": "running",
    }

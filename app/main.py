from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.api.ws import router as ws_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

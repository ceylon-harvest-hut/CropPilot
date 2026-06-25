from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.domains.inference.routes import router as inference_router
from app.domains.ingestion.routes import router as ingestion_router
from app.infrastructure.repositories.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="CropPilot",
    description="Crop knowledge ingestion and inference API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ingestion_router, prefix="/api/v1", tags=["ingestion"])
app.include_router(inference_router, prefix="/api/v1", tags=["inference"])

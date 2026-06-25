from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.domains.debug.routes import router as debug_router
from app.domains.inference.routes import router as inference_router
from app.domains.ingestion.routes import router as ingestion_router
from app.domains.lab.routes import router as lab_router
from app.infrastructure.config import get_settings
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

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router, prefix="/api/v1", tags=["ingestion"])
app.include_router(inference_router, prefix="/api/v1", tags=["inference"])
app.include_router(debug_router, prefix="/api/v1/debug", tags=["debug"])
app.include_router(lab_router, prefix="/api/v1/lab", tags=["lab"])

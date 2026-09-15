import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.routers import complaints, hotspots, wards

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NagaraRaksha API",
    description="Backend for the Hanamkonda civic reporting platform: "
    "waste/plastic/noise reports, hotspot detection, and cleanup verification.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(wards.router)
app.include_router(complaints.router)
app.include_router(hotspots.router)


@app.get("/health")
def health():
    return {"status": "ok"}

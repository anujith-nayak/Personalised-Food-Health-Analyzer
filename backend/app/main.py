"""
FastAPI Application Entry Point

Startup:
    uvicorn app.main:app --reload

Swagger UI:
    http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import models so SQLAlchemy registers them before create_all
from app.database.db import Base, engine
from app.models import user  # noqa: F401

from app.routes import auth, profile, health, dashboard, scanner

# Auto-create all database tables on startup (SQLite file created if not exists)
Base.metadata.create_all(bind=engine)

# Seed default food restriction rules if table is empty
from app.database.db import SessionLocal
from app.utils.food_restrictions import seed_rules
_db = SessionLocal()
try:
    seed_rules(_db)
finally:
    _db.close()

app = FastAPI(
    title="FoodHealth AI API",
    description="AI-Based Personalized Food Health Recommendation System — Phase 1",
    version="1.0.0",
)

# Allow Flutter app to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(scanner.router)


@app.get("/", tags=["Status"])
def root():
    return {"status": "running", "docs": "http://localhost:8000/docs"}

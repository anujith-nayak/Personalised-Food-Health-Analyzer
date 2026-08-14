"""
FastAPI Application Entry Point

Startup:
    uvicorn app.main:app --reload

Swagger UI:
    http://localhost:8001/docs
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Enable INFO logging so our debug prints appear in terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

# Import models so SQLAlchemy registers them before create_all
from app.database.db import Base, engine
from app.models import user, blood_report  # noqa: F401

from app.routes import auth, profile, health, dashboard, scanner, packaged_food, ai_nutrition, blood_report

# Auto-create all database tables on startup (SQLite file created if not exists)
Base.metadata.create_all(bind=engine)

# ── Run schema migrations (adds new columns to existing tables) ───────────────
# This is idempotent — safe to run on every startup.
# Handles SQLite (dev) and PostgreSQL (prod) automatically.
from app.database.migrate import run_migrations
run_migrations(engine)

# Seed default food restriction rules if table is empty
from app.database.db import SessionLocal
from app.utils.food_restrictions import seed_rules
from app.services.knowledge_base.seed_database import seed_knowledge_base

_db = SessionLocal()
try:
    seed_rules(_db)
    seed_knowledge_base()
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
app.include_router(packaged_food.router)  # Phase 2: Packaged food analysis
app.include_router(ai_nutrition.router)   # Phase 3: AI Nutrition Assistant
app.include_router(blood_report.router)    # Optional Blood Report module


@app.get("/", tags=["Status"])
def root():
    return {"status": "running", "docs": "http://localhost:8000/docs"}

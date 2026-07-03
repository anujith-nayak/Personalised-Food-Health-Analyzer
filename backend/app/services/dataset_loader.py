"""
Dataset Loader Service
Loads all CSV datasets once at startup and caches them in memory.
All other services import from this module — no repeated disk reads.
"""
import os
import pandas as pd

# Resolve path relative to this file's location
_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "datasets")

def _load(filename: str) -> pd.DataFrame:
    path = os.path.normpath(os.path.join(_BASE, filename))
    if not os.path.exists(path):
        print(f"[DatasetLoader] WARNING: {filename} not found at {path}")
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Normalize all string columns to lowercase stripped for easy matching
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    print(f"[DatasetLoader] Loaded {filename}: {len(df)} rows")
    return df

# ── Load once at module import time ──────────────────────────────────────────
allergy_rules      = _load("allergy_rules.csv")
health_rules       = _load("health_rules.csv")
health_r           = _load("health_r.csv")          # detailed multi-condition rules
ingredient_rules   = _load("ingredient_rules.csv")
recommended_foods  = _load("recommended_foods.csv")

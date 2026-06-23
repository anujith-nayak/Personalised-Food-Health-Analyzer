# FoodHealth AI — Phase 1

AI-Based Personalized Food Health Recommendation System  
Built with **Flutter** (frontend) + **FastAPI** (backend) + **SQLite** (database)

---

## Features

- User registration with BMI auto-calculation
- Health assessment with condition-specific sub-forms (Hypertension, Diabetes, Thyroid, PCOS, PCOD, Heart Disease, Kidney Disease, Obesity)
- Current health status tracking
- Rule-based food restriction engine (no AI required)
- Full dashboard with profile, BMI, health conditions, food restrictions, and completion tracker
- Edit profile (weight, height, age, food preference)
- JWT authentication (access + refresh tokens)
- Dark mode and light mode support
- Food scan placeholder page (Phase 2 ready)
- SQLite by default — zero database installation needed
- Easy switch to PostgreSQL by changing one environment variable

---

## Project Structure

```
major project/
├── backend/               FastAPI backend
│   ├── app/
│   │   ├── auth/          JWT logic and dependencies
│   │   ├── core/          Settings / config
│   │   ├── database/      SQLAlchemy engine and session
│   │   ├── models/        ORM table definitions
│   │   ├── routes/        API endpoints
│   │   ├── schemas/       Pydantic request/response models
│   │   ├── services/      Business logic
│   │   ├── utils/         BMI calculator, food restriction engine
│   │   └── main.py        App entry point
│   ├── .env               Environment variables
│   ├── requirements.txt
│   └── health_app.db      SQLite database (auto-created on first run)
│
└── frontend/              Flutter mobile app
    ├── lib/
    │   ├── constants/     Theme, app constants, base URL
    │   ├── models/        Dart data classes
    │   ├── providers/     Provider state management
    │   ├── screens/       All UI screens
    │   ├── services/      HTTP API calls
    │   ├── widgets/       Reusable widgets
    │   └── main.dart      App entry point
    └── pubspec.yaml
```

---

## Quick Start (10 minutes)

### Step 1 — Backend Setup

Open a terminal inside the `backend` folder:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn app.main:app --reload
```

The API will be running at: **http://localhost:8000**  
Swagger UI (API docs): **http://localhost:8000/docs**

> SQLite database file `health_app.db` is created automatically. No setup needed.

---

### Step 2 — Frontend Setup

Open a new terminal inside the `frontend` folder:

```bash
cd frontend
flutter pub get
flutter run
```

> If running on a **physical Android device**, update `baseUrl` in  
> `frontend/lib/constants/app_constants.dart` to your machine's local IP:
> ```dart
> static const String baseUrl = 'http://192.168.1.X:8000';
> ```
> Android emulator uses `10.0.2.2:8000` (already set as default).  
> iOS simulator uses `localhost:8000`.

---

## Environment Variables

Located at `backend/.env`:

```env
# SQLite (default — no installation needed)
DATABASE_URL=sqlite:///./health_app.db

# Uncomment to use PostgreSQL instead:
# DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/food_health_db

SECRET_KEY=change-this-secret-key-in-production-make-it-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

To switch to PostgreSQL, only change `DATABASE_URL`. No code changes needed.

---

## API Endpoints

| Method | Path                    | Auth | Description                        |
|--------|-------------------------|------|------------------------------------|
| POST   | /auth/register          | No   | Register new user, returns tokens  |
| POST   | /auth/login             | No   | Login, returns tokens              |
| POST   | /auth/refresh-token     | No   | Refresh access token               |
| GET    | /profile                | Yes  | Get user profile                   |
| PUT    | /profile                | Yes  | Update weight, height, age, pref   |
| POST   | /health-profile         | Yes  | Submit health assessment           |
| GET    | /health-profile         | Yes  | Get health profile                 |
| PUT    | /health-profile         | Yes  | Update health profile              |
| GET    | /dashboard              | Yes  | Full dashboard data                |
| GET    | /food-restrictions      | Yes  | Get food restrictions              |
| POST   | /scan/packaged-food     | Yes  | Phase 2 placeholder                |
| POST   | /scan/live-food         | Yes  | Phase 2 placeholder                |

---

## App Flow

```
Splash (3 sec)
    ↓
Login / Register
    ↓
Registration (name, email, password, age, gender, height, weight, food preference)
    ↓
BMI auto-calculated and stored
    ↓
Health Assessment (conditions + current status)
    ↓
Dashboard (profile, BMI, conditions, status, food restrictions, completion)
    ↓
Food Scan Selection (Phase 2 placeholder)
```

---

## Food Restriction Engine

No AI needed. Restrictions are generated by a rule table in `backend/app/utils/food_restrictions.py`.

| Condition      | Restricted Foods                                      |
|----------------|-------------------------------------------------------|
| Hypertension   | Chips, Pickles, Processed Foods, High Sodium Foods    |
| Diabetes       | Sugary Drinks, Chocolates, Candy, High Sugar Foods    |
| PCOS           | Sugary Foods, Deep Fried Foods, Processed Foods       |
| PCOD           | Sugary Foods, Junk Food, Processed Foods              |
| Kidney Disease | High Sodium Foods, High Potassium Foods               |
| Heart Disease  | Fried Foods, High Fat Foods, Trans Fats               |
| Thyroid        | Excess Processed Foods, Excess Soy Products           |
| Obesity        | High Calorie Snacks, Sugary Beverages, Fast Food      |

To add new rules, edit the `RULES` dictionary in that file. No other changes needed.

---

## Phase 2 — Future AI Integration Guide

The following hooks are already in place:

1. **`POST /scan/packaged-food`** — Add OCR + ingredient parsing logic here
2. **`POST /scan/live-food`** — Add food image classification model here
3. **Food restriction engine** (`utils/food_restrictions.py`) — Replace or augment rule table with ML predictions
4. **Database schema** — All tables are already designed to store scan results by adding a new `scan_results` table linked to `user_id`

Steps to integrate ML in Phase 2:
1. Train or load a model (TensorFlow Lite / PyTorch)
2. Add model inference to the scanner routes
3. Return structured food analysis results
4. Display results in the existing Flutter scan selection screen

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'app'` | Run uvicorn from inside the `backend` folder |
| Flutter can't connect to backend | Check `baseUrl` in `app_constants.dart` matches your setup |
| `401 Unauthorized` on API calls | Token expired — log out and log back in |
| Database errors on startup | Delete `health_app.db` and restart — it will be recreated |
| Physical device can't reach backend | Use `--host 0.0.0.0` flag: `uvicorn app.main:app --reload --host 0.0.0.0` |

# FoodHealth AI — Web Frontend

React + Vite + Tailwind CSS web app that connects to the FastAPI backend.

---

## Run Locally

### 1. Start the backend first
```bash
cd backend
venv\Scripts\activate          # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Run the web frontend
```bash
cd web
npm install        # first time only
npm run dev
```

Open **http://localhost:3000** in your browser.

The Vite dev server automatically proxies `/api/*` → `http://localhost:8000/*` so no CORS issues.

---

## Push to GitHub

```bash
# From the project root
git init
git add .
git commit -m "Initial commit — FoodHealth AI Phase 1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

---

## Deploy — Netlify (recommended, free)

1. Go to **https://app.netlify.com** → New site → Import from GitHub
2. Set build settings:
   - Base directory: `web`
   - Build command: `npm run build`
   - Publish directory: `web/dist`
3. Add environment variable:
   - `VITE_API_URL` = your deployed backend URL (e.g. from Render)
4. Open `web/netlify.toml` and replace `your-backend-url.onrender.com` with your actual backend URL
5. Click Deploy

Netlify handles React Router redirects automatically via `netlify.toml`.

---

## Deploy — Vercel (alternative, free)

1. Go to **https://vercel.com** → New Project → Import from GitHub
2. Set root directory to `web`
3. Add environment variable: `VITE_API_URL` = your backend URL
4. Open `web/vercel.json` and replace the backend URL
5. Click Deploy

---

## Deploy Backend — Render (free tier)

1. Go to **https://render.com** → New Web Service → Connect GitHub
2. Set:
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables from `backend/.env`
4. For production, switch `DATABASE_URL` to a PostgreSQL database (Render offers free PostgreSQL)

---

## Project Structure

```
web/
├── src/
│   ├── api/           HTTP client + API functions
│   ├── components/    Reusable UI components
│   ├── context/       Auth context (React Context API)
│   ├── pages/         All page components
│   │   ├── LandingPage.jsx
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── BmiPage.jsx
│   │   ├── HealthAssessmentPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── EditProfilePage.jsx
│   │   └── ScanPage.jsx
│   ├── App.jsx        Routes
│   ├── main.jsx       Entry point
│   └── index.css      Tailwind + custom styles
├── netlify.toml       Netlify deploy config
├── vercel.json        Vercel deploy config
├── vite.config.js     Vite config with API proxy
└── package.json
```

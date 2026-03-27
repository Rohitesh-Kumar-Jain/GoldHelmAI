# AuricAI

AuricAI is a production-style V1 for gold futures analysis and next-trading-day prediction. The stack uses FastAPI for the API, a lightweight tree-based regression model for inference, `yfinance` for market data, and a Vite/React frontend for the dashboard.

## Current Architecture

```text
AuricAI/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   ├── data/
│   └── requirements.txt
├── frontend/
│   ├── public/
│   └── src/
└── README.md
```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Notes:

- The correct Uvicorn target is `app.main:app`.
- Market endpoints are served under `/api`.
- `ALLOWED_ORIGINS` should include the deployed Vercel domain.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` when the backend runs on a non-default URL.

## API Endpoints

- `GET /health`
- `GET /api/price`
- `GET /api/history`
- `GET /api/predict`

`/api/predict` returns:

- Latest prediction price
- Predicted percentage move
- Confidence score derived from validation error
- Validation MAE for recent holdout data

## Deployment Notes

### Render Backend

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Root directory: `backend`
- Environment variables:
  - `APP_ENV=production`
  - `ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app`
  - `DATA_LOOKBACK_DAYS=180`
  - `MODEL_MIN_ROWS=45`

### Vercel Frontend

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable:
  - `VITE_API_BASE_URL=https://your-render-service.onrender.com`

## Recommended Next Structure

If the project grows, keep the current layout but add these modules incrementally rather than rewriting:

- `app/core/` for logging, exception handlers, and shared app wiring
- `app/repositories/` if database persistence is introduced
- `app/ml/` for training jobs, backtesting, and model artifact persistence
- `tests/` for API, data, and model behavior coverage
# GoldHelmAI

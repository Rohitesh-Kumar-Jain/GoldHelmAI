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

<img width="1408" height="768" alt="Gemini_Generated_Image_s9cbnts9cbnts9cb (1)" src="https://github.com/user-attachments/assets/8b15384d-b6ae-4477-8310-5031067685d5" />

System Architecture Diagram

<img width="1897" height="1856" alt="mermaid-diagram (2)" src="https://github.com/user-attachments/assets/deae3bb5-abe4-47e7-95ad-f2186af5d342" />

Sequence Diagram (End-to-End Flow)

<img width="4728" height="2262" alt="mermaid-diagram (3)" src="https://github.com/user-attachments/assets/1ded919f-e0b1-46e1-af29-ff4ef131cb19" />

RL Agent State Machine

<img width="822" height="871" alt="mermaid-diagram (6)" src="https://github.com/user-attachments/assets/adace017-71c1-48cf-b519-f5170d73e5a1" />

ML Pipeline Diagram (Offline + Online)

<img width="2811" height="920" alt="mermaid-diagram (5)" src="https://github.com/user-attachments/assets/bfd013e8-0e11-43f2-8488-2ab643d30cbc" />

Data Flow Diagram (DFD)

<img width="3098" height="326" alt="mermaid-diagram (4)" src="https://github.com/user-attachments/assets/cc9c231b-0173-40a0-bb21-1ef19bcd79da" />




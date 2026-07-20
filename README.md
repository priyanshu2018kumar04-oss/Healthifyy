# Healthify AI Agent

AI-powered personal health monitoring and planning system built with **LangGraph**, **Groq (LLaMA 3.3)**, **FastAPI**, and a vanilla HTML/JS frontend.

## Project Structure

```
Healthify/
├── agent/          # LangGraph AI model (Groq) — standalone, deployable separately
│   ├── graph.py    # StateGraph pipeline definition
│   ├── nodes.py    # 6 processing nodes (input → warnings → diet → workout → progress)
│   ├── state.py    # Agent state schema
│   ├── llm.py      # Groq LLM config
│   ├── health_calc.py
│   └── run.py      # CLI to test agent without backend
├── backend/        # FastAPI REST API, SQLite DB, auth, notifications
│   ├── main.py
│   ├── routers/
│   ├── services/   # Email (SMTP), WhatsApp (Twilio), scheduler
│   └── .env        # Your secrets (copy from .env.example)
└── frontend/       # Static web UI (login, health input, plans, progress)
    ├── index.html
    ├── dashboard.html
    ├── health-input.html
    ├── plan.html
    └── progress.html
```

## Features

| Feature | Description |
|---------|-------------|
| **Auth** | Register/login with name, age, gender, email, height, activity level |
| **Health logging** | Weight (kg/lbs/stone), fasting glucose (mmol/L or mg/dL), optional BP, cholesterol, post-meal sugar |
| **Goals** | Fat loss, weight gain, bodybuilding, or balanced maintenance + AI recommendation by BMI |
| **AI diet plan** | Full-day meals with calories, macros, protein, GI index, grocery list |
| **AI workout plan** | Exercises with calorie burn, optional yoga, weekly schedule |
| **Warning system** | Alerts for obese/underweight, glucose, BP, cholesterol, sugar spikes |
| **Weekly progress** | AI summary, health score, trends, forward recommendations |
| **Notifications** | Email (Gmail SMTP) + WhatsApp (Twilio) for alerts and reports |

## LangGraph Pipeline

```
START → input_processor → health_analyzer → warning_detector
      → diet_plan (Groq) → workout_plan (Groq) → [progress_tracker?] → END
```

## Quick Start

### 1. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # Then edit .env with your keys
python -m uvicorn main:app --reload --port 8000
```

Or double-click `backend/start.bat`.

API docs: http://localhost:8000/docs

### 2. Frontend setup

```bash
cd frontend
python -m http.server 5500
```

Or double-click `frontend/start.bat`.

Open: http://localhost:5500

### 3. Test agent standalone (optional)

```bash
pip install -r agent/requirements.txt
python agent/run.py
```

## Environment Variables (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | **Yes** | Free key from [console.groq.com](https://console.groq.com) |
| `SECRET_KEY` | **Yes** | JWT secret (32+ chars) |
| `SMTP_EMAIL` / `SMTP_PASSWORD` | Optional | Gmail app password for email alerts |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Optional | WhatsApp via Twilio sandbox |
| `FRONTEND_URL` | Optional | Default `http://localhost:5500` |

## User Flow

1. **Register** at `/index.html` (name, age, gender, email, height, WhatsApp optional)
2. **Log health data** — weight, glucose, optional BP/cholesterol/post-meal sugar
3. **Set goal** — fat loss / weight gain / bodybuilding / maintain (with BMI-based recommendation)
4. **Generate AI plan** — diet + workout + warnings; stored in SQLite
5. **View progress** — weekly report, trends, email/WhatsApp notifications

## API Endpoints (summary)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/health/log` | Log health metrics |
| POST | `/api/health/goal` | Set fitness goal |
| POST | `/api/plan/generate` | Run LangGraph AI pipeline |
| GET | `/api/plan/diet/latest` | Latest diet plan |
| GET | `/api/progress/weekly/latest` | Latest weekly report |
| POST | `/api/progress/weekly/generate` | Trigger weekly report |

## Deploying in Another IDE

Each folder is self-contained:

- **agent/** — copy + set `GROQ_API_KEY`; run `python agent/run.py`
- **backend/** — copy + `pip install -r requirements.txt` + `.env`
- **frontend/** — serve statically; update `API_BASE` in `frontend/js/api.js` if backend URL changes

## Disclaimer

This is an AI health assistant, **not** a substitute for professional medical advice. Always consult a qualified doctor for medical decisions.

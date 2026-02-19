# 🛡️ Autonomous CI/CD Healing Agent

**RIFT 2026 Hackathon — AI/ML · DevOps Automation · Agentic Systems Track**

An autonomous agent that clones a GitHub repository, detects code issues (syntax errors, logic bugs, type errors, import failures, linting violations, indentation problems), generates fixes using an LLM, and pushes corrected code to a new branch — all monitored through a live React dashboard.

---

## 🌐 Deployment

| Resource | URL |
|----------|-----|
| **Live Dashboard** | *(Add your deployment URL here)* |
| **LinkedIn Video** | *(Add your LinkedIn video URL here)* |
| **GitHub Repository** | https://github.com/Code71590/RIFT-Hack1 |

---

## 🏗️ Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                   REACT DASHBOARD                     │
│  ┌──────────┐ ┌────────────┐ ┌────────────────────┐  │
│  │  Input   │ │ Live Feed  │ │  Summary + Score   │  │
│  │  Form    │ │  (SSE)     │ │  Breakdown Panel   │  │
│  └────┬─────┘ └──────▲─────┘ └────────────────────┘  │
│       │              │                                │
│       ▼              │                                │
│  ┌───────────────────┴──────────┐                     │
│  │     Nginx Reverse Proxy      │                     │
│  └───────────────┬──────────────┘                     │
└──────────────────┼───────────────────────────────────┘
                   │ /api/*
┌──────────────────▼───────────────────────────────────┐
│               FLASK API SERVER                        │
│  ┌──────────────────────────────────────────────┐     │
│  │           Pipeline Orchestrator               │     │
│  │  ┌────────┐ ┌──────────┐ ┌───────────────┐   │     │
│  │  │ Clone  │→│ Analyze  │→│ Test Runner   │   │     │
│  │  └────────┘ └──────────┘ └───────┬───────┘   │     │
│  │                                  │            │     │
│  │  ┌───────────────────────────────▼─────────┐  │     │
│  │  │   Pass 1: Deterministic Fixer (no LLM)  │  │     │
│  │  │   SYNTAX · IMPORT · LINTING · INDENT    │  │     │
│  │  └───────────────────┬─────────────────────┘  │     │
│  │                      ▼                        │     │
│  │  ┌───────────────────────────────────────┐    │     │
│  │  │   Pass 2: LLM Fixer (if needed)       │    │     │
│  │  │   LOGIC · TYPE_ERROR                  │    │     │
│  │  └──────────────┬────────────────────────┘    │     │
│  │                 ▼                             │     │
│  │  ┌──────────────────────────────────────┐     │     │
│  │  │   Git Ops: Commit + Push to Branch   │     │     │
│  │  │   [AI-AGENT] prefixed commits        │     │     │
│  │  └──────────────────────────────────────┘     │     │
│  └──────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
RIFT-Hack1/
├── docker-compose.yml        # Docker orchestration
├── backend/                  # Flask API + Agent pipeline
│   ├── Dockerfile            # Backend container
│   ├── app.py                # Flask server (port 5000)
│   ├── requirements.txt      # Python dependencies
│   ├── agent/                # Core agent modules
│   │   ├── pipeline.py       # Orchestrator — runs the full healing pipeline
│   │   ├── clone.py          # Clones GitHub repos to workspace/
│   │   ├── analyzer.py       # Analyzes repo structure and file types
│   │   ├── test_runner.py    # Runs pytest + flake8 and parses output
│   │   ├── deterministic_fixer.py  # Fixes SYNTAX/IMPORT/LINTING/INDENT without LLM
│   │   ├── fixer.py          # Applies code fixes to files
│   │   ├── llm.py            # LLM integration (OpenRouter / Cerebras / Gemini)
│   │   └── git_ops.py        # Git operations (branch, commit, push)
│   └── workspace/            # Cloned repos land here at runtime
├── frontend/                 # React + Vite dashboard
│   ├── Dockerfile            # Frontend container (multi-stage + Nginx)
│   ├── nginx.conf            # Nginx config (SPA + API proxy)
│   ├── src/
│   │   ├── App.jsx           # Main dashboard UI
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── Hackathon_Problem_Statement/
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** + **Docker Compose** (recommended)
- Or: Python 3.10+, Node.js 18+, Git

### Option A: Docker (Recommended)

```bash
# 1. Clone the project
git clone https://github.com/Code71590/RIFT-Hack1.git
cd RIFT-Hack1

# 2. Configure environment
# Edit backend/.env with your API keys (GITHUB_TOKEN, LLM keys)

# 3. Build and run
docker compose build
docker compose up -d

# 4. Open http://localhost in your browser
```

The app runs on **port 80** — frontend and API are served through a single Nginx endpoint.

### Option B: Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py
# Flask API at http://localhost:5000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# React dashboard at http://localhost:5173
```

---

## 🖥️ Dashboard Features

1. **Input Section** — Enter GitHub repo URL, team name, leader name → click "Run Agent"
2. **Run Summary Card** — Shows repo URL, branch name, total failures, final CI/CD status badge
3. **Score Breakdown Panel** — Base 100 pts, speed bonus (+10 if <5 min), efficiency penalty (-2 per commit over 20)
4. **Fixes Applied Table** — File | Bug Type | Line | Commit Message | Status (✅/❌)
5. **CI/CD Status Timeline** — Pass/fail badge per iteration with timestamps
6. **Live Event Feed** — Real-time SSE streaming of pipeline progress

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Start the agent pipeline |
| `GET` | `/api/status` | Get current run status + results |
| `GET` | `/api/events` | SSE stream for real-time events |
| `GET` | `/api/results` | Get the latest results.json |
| `GET` | `/api/health` | Health check |

**POST `/api/run` body:**
```json
{
  "repo_url": "https://github.com/Code71590/dummy-buggy-repo",
  "team_name": "RIFT_ORGANISERS",
  "leader_name": "Saiyam_Kumar"
}
```

---

## 🧪 Test Repository

A dummy repository with **8 intentional bugs** across all 6 bug types is available:

**URL:** https://github.com/Code71590/dummy-buggy-repo

| Bug Type | Count | Files |
|----------|-------|-------|
| LINTING | 1 | `utils.py` |
| SYNTAX | 1 | `validator.py` |
| LOGIC | 2 | `utils.py`, `data_processor.py` |
| IMPORT | 1 | `data_processor.py` |
| TYPE_ERROR | 1 | `config.py` |
| INDENTATION | 2 | `formatter.py` |

---

## 🐛 Supported Bug Types

| Bug Type | Detection Method | Fix Strategy |
|----------|-----------------|--------------|
| SYNTAX | `ast.parse()` | Deterministic (no LLM) |
| IMPORT | `importlib` check | Deterministic (no LLM) |
| LINTING | `flake8 --select=F401` | Deterministic (no LLM) |
| INDENTATION | `flake8 --select=E111,E117` | Deterministic (no LLM) |
| LOGIC | Test failure analysis | LLM-powered |
| TYPE_ERROR | Test failure analysis | LLM-powered |

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------:|
| Frontend | React 19, Vite 5, Vanilla CSS |
| Backend | Python 3.12, Flask 3.1 |
| Agent | Two-pass: Deterministic + LLM |
| LLM Providers | OpenRouter, Cerebras, Gemini |
| CI/CD | GitHub Actions |
| Containerization | Docker, Docker Compose, Nginx |
| State Management | React Context API |
| Real-time | Server-Sent Events (SSE) |

---

## ⚙️ Environment Setup

Create a `backend/.env` file:

```env
# LLM Provider: "openrouter", "cerebras", or "gemini"
LLM_PROVIDER=gemini

# GitHub Token for pushing fixes
GITHUB_TOKEN=your_github_token_here

# Gemini (recommended)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-flash-latest

# OpenRouter (alternative)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free

# Cerebras (alternative)
CEREBRAS_API_KEY=your_cerebras_key
CEREBRAS_MODEL=qwen-3-235b-a22b-instruct-2507
```

---

## ⚠️ Known Limitations

- Agent currently supports **Python repositories** only
- Requires public GitHub repos (or adequate token permissions for private repos)
- LLM fixes depend on API availability and rate limits
- CI/CD monitoring relies on GitHub Actions being configured in the target repo

---

## 👥 Team

**RIFT 2026 Hackathon — Multi-city · AIML Track**

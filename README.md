# 🛡️ Autonomous CI/CD Healing Agent

**RIFT 2026 Hackathon — AI/ML · DevOps Automation · Agentic Systems Track**

An autonomous agent that clones a GitHub repository, detects code issues (syntax errors, logic bugs, type errors, import failures, linting violations, indentation problems), generates fixes using an LLM, and pushes corrected code to a new branch — all monitored through a live React dashboard.

---

## 📁 Project Structure

```
RIFT-Hack1/
├── backend/                  # Flask API + Agent pipeline
│   ├── app.py                # Flask server (port 5000)
│   ├── requirements.txt      # Python dependencies
│   ├── agent/                # Core agent modules
│   │   ├── pipeline.py       # Orchestrator — runs the full healing pipeline
│   │   ├── clone.py          # Clones GitHub repos to workspace/
│   │   ├── analyzer.py       # Analyzes repo structure and file types
│   │   ├── test_runner.py    # Runs pytest + flake8 and parses output
│   │   ├── fixer.py          # Generates code fixes per bug
│   │   ├── llm.py            # LLM integration for fix generation
│   │   └── git_ops.py        # Git operations (branch, commit, push)
│   └── workspace/            # Cloned repos land here at runtime
├── frontend/                 # React + Vite dashboard
│   ├── src/
│   │   ├── App.jsx           # Main dashboard UI
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── dummy-buggy-repo/         # Test repo with 8 intentional bugs
│   └── (see dummy-buggy-repo/README.md for details)
└── Hackathon_Problem_Statement/  # Problem statement images
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (with pip)
- **Node.js 18+** (with npm)
- **Git** installed and authenticated with GitHub
- **GitHub CLI** (`gh`) — optional, for repo creation

### 1. Clone the Project

```bash
git clone https://github.com/Code71590/RIFT-Hack1.git
cd RIFT-Hack1
```

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The Flask API will start at **http://localhost:5000**.

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Start the agent pipeline |
| `GET` | `/api/status` | Get current run status + results |
| `GET` | `/api/health` | Health check |

**POST `/api/run` body:**
```json
{
  "repo_url": "https://github.com/Code71590/dummy-buggy-repo",
  "team_name": "RIFT_ORGANISERS",
  "leader_name": "Saiyam_Kumar"
}
```

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The React dashboard will start at **http://localhost:5173**.

---

## 🖥️ Dashboard Features

1. **Input Section** — Enter GitHub repo URL, team name, leader name → click "Run Agent"
2. **Run Summary Card** — Shows repo URL, branch name, total failures, final CI/CD status
3. **Score Breakdown** — Base 100 pts, speed bonus, efficiency penalty
4. **Fixes Applied Table** — File | Bug Type | Line | Commit Message | Status (✅/❌)
5. **CI/CD Timeline** — Pass/fail badge per iteration with timestamps

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

See [`dummy-buggy-repo/error_summary.txt`](dummy-buggy-repo/error_summary.txt) for full details.

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 5, Vanilla CSS |
| Backend | Python 3.12, Flask 3.1 |
| Agent | GitPython, pytest, flake8 |
| CI/CD | GitHub Actions |

---

## 👥 Team

**RIFT 2026 Hackathon — Multi-city · AIML Track**

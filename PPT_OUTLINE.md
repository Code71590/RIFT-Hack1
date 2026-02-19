# 🛡️ Autonomous CI/CD Healing Agent — Presentation Outline

> **RIFT 2026 Hackathon · AI/ML · DevOps · Agentic Systems Track**
> Clean, minimal, professional slide deck — dark theme recommended

---

## Slide 1 — Title Slide

- **Title:** Autonomous CI/CD Healing Agent
- **Subtitle:** Self-Healing Code Pipelines Powered by AI
- **Team Name** + **Leader Name**
- **Event:** RIFT 2026 Hackathon — AIML Track
- **Visual:** Subtle animated code/pipeline glyph background

---

## Slide 2 — The Problem

- **Headline:** "Developers spend 40–60% of their time debugging CI/CD failures"
- **Pain Points (3 icons):**
  - 🧪 Test failures block entire teams
  - 🔁 Manual fix-commit-push loops waste hours
  - 📉 Pipeline failures delay production releases
- **Visual:** A red-highlighted failing CI/CD pipeline diagram

---

## Slide 3 — Our Solution

- **Headline:** One-Click Autonomous Bug Fixer
- **Key Message:** "Paste a GitHub URL → Our agent clones, detects, fixes, and pushes — zero human intervention"
- **Flow (left-to-right):**
  `Repo URL → Clone → Analyze → Fix → Commit → Push → CI/CD Pass ✅`
- **Visual:** Clean horizontal pipeline flow graphic

---

## Slide 4 — Architecture Diagram

- **Full system diagram:**

```
┌───────── React Dashboard ─────────┐
│  Input Form  │ Live SSE Feed      │
│  Summary     │ Score Breakdown    │
└──────────────┼────────────────────┘
               │ /api/*
┌──────────────▼────────────────────┐
│         Flask API Server          │
│  ┌────────────────────────────┐   │
│  │   Pipeline Orchestrator    │   │
│  │  Clone → Analyze → Test   │   │
│  │  Pass 1: Deterministic    │   │
│  │  Pass 2: LLM (Gemini)    │   │
│  │  Git Ops: Branch + Push   │   │
│  └────────────────────────────┘   │
└───────────────────────────────────┘
```

- **Call out:** Two-pass fixing strategy (deterministic first, LLM second)

---

## Slide 5 — Two-Pass Fix Strategy

| Pass | What It Fixes | How |
|------|---------------|-----|
| **Pass 1: Deterministic** | SYNTAX, IMPORT, LINTING, INDENTATION | `ast.parse()`, `flake8`, `importlib` — no API calls |
| **Pass 2: LLM-Powered** | LOGIC, TYPE_ERROR | Google Gemini API with 3-key failover |

- **Advantage:** Fast, cheap, and reliable — LLM is only used when truly needed
- **Visual:** Side-by-side comparison cards

---

## Slide 6 — 6 Bug Types Supported

| Bug Type | Detection | Fix |
|----------|-----------|-----|
| SYNTAX | `ast.parse()` | Auto-correct syntax |
| IMPORT | `importlib` check | Add/fix import statements |
| LINTING | `flake8 --select=F401` | Remove unused imports |
| INDENTATION | `flake8 --select=E111,E117` | Fix whitespace |
| LOGIC | Test failure analysis | LLM-generated fix |
| TYPE_ERROR | Test failure analysis | LLM-generated fix |

- **Visual:** Icon grid with 6 colored cards

---

## Slide 7 — Live Dashboard Demo

- **Screenshot / Screen Recording of the React dashboard** showing:
  1. Input form with repo URL, team name, leader name
  2. Run Summary Card with CI/CD status badge
  3. Score Breakdown Panel (base 100 + speed bonus – efficiency penalty)
  4. Fixes Applied Table (file, bug type, line, commit, status)
  5. CI/CD Status Timeline (pass/fail per iteration)
  6. Live SSE event feed
- **Visual:** Full-width screenshot or embedded video

---

## Slide 8 — Real-Time SSE Streaming

- **Headline:** "Watch the agent work in real-time"
- **Key Points:**
  - Server-Sent Events push pipeline updates to the dashboard live
  - Every step: clone, analyze, test, fix, commit, push — all streamed
  - No polling — instant feedback
- **Visual:** Animated event feed mockup

---

## Slide 9 — Smart API Key Failover

- **Headline:** Built for Resilience
- **Flow diagram:**

```
Key #1 → 429/403? → Key #2 → 429/403? → Key #3
   ↓                    ↓                    ↓
  Success             Success              Success
```

- **Key Points:**
  - 3 Gemini API keys with automatic round-robin rotation
  - Retries with exponential backoff before rotating
  - Prevents pipeline failure due to rate limits
- **Visual:** Shield/resilience icon

---

## Slide 10 — Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 5, Vanilla CSS |
| **Backend** | Python 3.12, Flask 3.1 |
| **Agent** | Two-pass: Deterministic + LLM |
| **LLM Provider** | Google Gemini (gemini-3-flash-preview) |
| **CI/CD** | GitHub Actions |
| **Containers** | Docker, Docker Compose, Nginx |
| **Real-time** | Server-Sent Events (SSE) |
| **Deployment** | Render (Frontend + Backend) |

- **Visual:** Clean tech logo grid

---

## Slide 11 — Scoring System

- **Base Score:** 100 points
- **Speed Bonus:** +10 if completed in < 5 minutes
- **Efficiency Penalty:** −2 per commit over 20
- **Final Score** displayed prominently with progress bar
- **Visual:** Score gauge / donut chart

---

## Slide 12 — Git Operations

- **Branch Naming:** `TEAM_NAME_LEADER_NAME_AI_Fix` (auto-generated)
- **Commit Prefixes:** All commits start with `[AI-AGENT]`
- **Never pushes to main** — always creates a new branch
- **Visual:** Git branch diagram showing main → AI_Fix branch

---

## Slide 13 — Deployment

| Service | URL |
|---------|-----|
| **Frontend** | https://rift-frontend.onrender.com |
| **Backend API** | https://rift-backend-je0t.onrender.com |
| **GitHub Repo** | https://github.com/Code71590/RIFT-Hack1 |

- **One-click deploy:** Render Blueprint (`render.yaml`)
- **Docker Compose** for local development
- **Visual:** Deployment architecture with Render logo

---

## Slide 14 — Live Demo (if presenting)

- **Steps:**
  1. Open dashboard at live URL
  2. Paste dummy buggy repo: `https://github.com/Code71590/dummy-buggy-repo`
  3. Enter team name and leader name
  4. Click "Run Agent" → Watch SSE stream in real-time
  5. Show fixes applied, CI/CD timeline, and final score
- **Visual:** Live screen share

---

## Slide 15 — Thank You

- **Title:** Thank You!
- **Team members** (names + roles)
- **Links:**
  - 🌐 Live: https://rift-frontend.onrender.com
  - 💻 GitHub: https://github.com/Code71590/RIFT-Hack1
  - 🎥 LinkedIn Video: *(add link)*
- **Visual:** Clean closing with team photo or avatars

---

## 🎨 Design Guidelines

| Aspect | Recommendation |
|--------|---------------|
| **Theme** | Dark mode (charcoal/navy background, white text) |
| **Accent Colors** | Emerald green (#10B981) for success, warm amber (#F59E0B) for highlights |
| **Typography** | Inter or Outfit (Google Fonts) — clean sans-serif |
| **Layout** | Max 5–6 bullet points per slide, lots of whitespace |
| **Icons** | Use Lucide or Phosphor icon set for consistency |
| **Diagrams** | Flat, minimal line art — avoid 3D or clip art |
| **Animations** | Subtle fade-in per element, no flashy transitions |
| **Aspect Ratio** | 16:9 widescreen |

> **Pro tip:** Use Figma, Canva (dark theme template), or Google Slides with a custom dark theme.
> Keep text large (24pt+ body, 40pt+ headings). Let visuals do the talking.

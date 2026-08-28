# JEE Doubt Resolution & Companion Studio

A full-stack AI-assisted pedagogical platform designed for JEE Main & JEE Advanced aspirants. The platform uses a 3-tier progressive hint framework rather than dumping direct solutions, guiding students step-by-step through Socratic questioning, formula setups, and KaTeX mathematical notation.

---

## 🏗️ Architecture & Monorepo Structure

```
jee-doubt-solver/
├── AGENTS.md                   # Pedagogical rules & syllabus boundary specifications
├── docker-compose.yml          # Local orchestration for Redis (6379) & Qdrant (6333)
├── README.md                   # Documentation & quickstart guide
│
├── backend/                    # Python FastAPI application
│   ├── requirements.txt        # fastapi, uvicorn, redis, qdrant-client, langchain, pydantic, tiktoken
│   ├── .env.example            # Environment variables configuration
│   └── app/
│       ├── main.py             # FastAPI entrypoint, CORS, lifespan, & WebSockets
│       ├── api/
│       │   └── v1/
│       │       ├── router.py   # Aggregated API router
│       │       ├── doubts.py   # POST /intake, GET /{session_id}
│       │       ├── hints.py    # POST /progress (Tier 1-3), POST /attempt
│       │       └── studio.py   # GET /topics, GET /artifacts, POST /generate, GET /download
│       ├── core/
│       │   ├── config.py       # Pydantic Settings & environment variables
│       │   ├── redis.py        # Async Redis session client with local memory fallback
│       │   └── security.py     # Security headers middleware & API key verification
│       ├── schemas/
│       │   ├── session.py      # SessionState, HintTierEnum, SubjectEnum
│       │   ├── doubts.py       # Doubt intake & syllabus validation models
│       │   ├── hints.py        # 3-Tier progressive hints & student attempts
│       │   └── studio.py       # Topics, study artifacts, and generation schemas
│       └── services/
│           ├── vision_ocr.py   # Multimodal math OCR & LaTeX transcription
│           ├── rag_engine.py   # Qdrant vector retrieval for JEE concept banks
│           ├── multi_llm_consensus.py # Multi-model verification & hint synthesis
│           └── guardrails.py   # Strict JEE syllabus boundary & anti-leak filters
│
└── frontend/                   # React + Vite + Tailwind CSS + Lucide Icons + KaTeX
    ├── package.json            # Dependencies & build scripts
    ├── vite.config.js          # Vite configuration with /api and /ws proxy
    ├── tailwind.config.js      # Tailwind CSS configuration with JEE theme colors
    ├── postcss.config.js       # PostCSS plugins
    ├── index.html              # KaTeX CSS & DOM root
    └── src/
        ├── App.jsx             # Root layout orchestrating Doubt Solver & Studio
        ├── main.jsx            # React 18 DOM mount
        ├── index.css           # Tailwind directives & KaTeX custom styles
        ├── services/
        │   └── api.js          # HTTP fetch API & WebSocket client wrapper
        └── components/
            ├── Navbar.jsx      # Top navigation & active session status
            ├── chat/
            │   ├── DoubtInput.jsx         # Text/image intake, subject tabs, samples
            │   ├── HintProgressionView.jsx# 3-Tier progressive hint renderer & attempt tester
            │   └── LatexRenderer.jsx      # KaTeX inline ($...$) and block ($$...$$) math renderer
            └── studio/
                ├── StudioDashboard.jsx    # Companion Studio workspace
                ├── TopicSelector.jsx      # Subject & syllabus topic explorer
                └── ArtifactCard.jsx       # Artifact previews & markdown downloads
```

---

## 🚀 Quickstart Guide

### 1. Start Infrastructure (Redis & Qdrant)
```bash
docker-compose up -d
```
- **Redis**: Running on `localhost:6379`
- **Qdrant**: Running on `localhost:6333` (gRPC on `6334`)

### 2. Backend Setup & Launch
```bash
cd backend
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- WebSocket Endpoint: `ws://localhost:8000/ws/session/{session_id}`

### 3. Frontend Setup & Launch
```bash
cd frontend
npm install
npm run dev
```
- App UI: [http://localhost:5173](http://localhost:5173)

---

## 🎯 3-Tier Progressive Hint Protocol

1. **Tier 1: Conceptual Nudge**
   - Identifies underlying laws and governing principles.
   - Highlights relevant formulas in LaTeX without problem-specific substitutions.
   - Poses a reflective leading question to prompt initial formulation.
2. **Tier 2: Structural Strategy & Roadmap**
   - Breaks the problem into actionable sub-steps.
   - Outlines coordinate conventions, free-body diagrams, and setup equations.
   - Highlights common JEE pitfalls.
3. **Tier 3: Detailed Walkthrough**
   - Steps through 80–90% of intermediate algebra.
   - Prompts the student to evaluate the final substitution and sanity-check the result.

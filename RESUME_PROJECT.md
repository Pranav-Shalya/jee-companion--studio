# 🚀 JEE Companion Studio – Resume Project Showcase

> **Project Title**: **JEE Companion Studio – Full-Stack Distributed AI Doubt Resolution & Adaptive Assessment Platform**  
> **Role**: Full-Stack AI Engineer / System Architect  
> **GitHub**: [github.com/Pranav-Shalya/jee-companion--studio](https://github.com/Pranav-Shalya/jee-companion--studio)

---

## 🛠️ Technical Stack

```text
Frontend:     React 18 • Vite • Tailwind CSS • KaTeX (LaTeX Math Rendering) • Clerk Auth • WebSocket Client
Backend:      FastAPI • Python 3.12 • Uvicorn • Asynchronous WebSockets • Async SQLAlchemy (aiosqlite) • Redis
AI / RAG:     Qdrant Cloud Vector DB • FastEmbed (ONNX BAAI/bge-small-en-v1.5) • Groq (LLaMA 3.3 70B) • Google Gemini 1.5 Flash • Key Pool Rotator
DevOps/Cloud: Docker • Docker Compose • GitHub Actions (CI/CD) • Render • Vercel
```

---

## 📄 Bullet Points for Resume (XYZ / STAR Format)

### Option 1: AI / Machine Learning & RAG Focused Roles
* **Engineered a sub-100ms dense semantic retrieval pipeline** using ONNX-optimized **FastEmbed** (`BAAI/bge-small-en-v1.5`, 384 dimensions) and **Qdrant Cloud Vector DB**, applying deterministic UUID5 deduplication to index and query past-year JEE question archives.
* **Architected a multi-LLM consensus & routing engine** combining **Groq (LLaMA 3.3 70B)** and **Google Gemini 1.5 Flash** with an automated API key pool rotator and exponential backoff, preventing 429 rate limits and generating authentic test papers with complete KaTeX step derivations.
* **Designed a 3-tier progressive hint scaffolding system** (Conceptual Nudge $\rightarrow$ Structural Strategy $\rightarrow$ Detailed Walkthrough) with regex guardrails to prevent answer leakage and foster active Socratic problem-solving.
* **Integrated cognitive memory modeling via the Ebbinghaus Forgetting Curve** ($R = e^{-t/S}$), analyzing student test telemetry to calculate optimal spaced repetition review intervals ($I = -S \ln(R_{\text{target}})$) and weak-area heatmaps.

### Option 2: Full-Stack & Backend Systems Engineering Roles
* **Built an asynchronous, bidirectional WebSocket layer** in **FastAPI** (`/ws/mentor/{session_id}`) with stateful session caching in **Redis** and **SQLite (Async SQLAlchemy)**, delivering real-time speculative thought streaming and interactive Socratic hints.
* **Developed a responsive, multimodal React 18 frontend** using **Vite**, **Tailwind CSS**, and **KaTeX**, featuring client-side LaTeX equation rendering, dark-mode styling, and **Clerk** authentication.
* **Containerized backend microservices with Docker and Docker Compose**, implementing multi-stage builds and layer caching that reduced container build times by 40% on production environments.
* **Established production CI/CD workflows via GitHub Actions**, deploying a decoupled architecture on **Render** (FastAPI) and **Vercel** (React SPA) with dynamic regex-based CORS policies for secure preview and production domain routing.

---

## 🏛️ System Architecture Summary

```text
                      ┌────────────────────────────────────────┐
                      │    Vercel React 18 SPA (Vite)          │
                      │  • KaTeX Formula Engine • Clerk Auth   │
                      └──────────────────┬─────────────────────┘
                                         │ HTTPS / WSS
                                         ▼
                      ┌────────────────────────────────────────┐
                      │    Render FastAPI Asynchronous Engine   │
                      │  • Rate Limiting • CORS Regex Security  │
                      └──────┬───────────┬──────────────┬──────┘
                             │           │              │
           ┌─────────────────┘           │              └────────────────┐
           ▼                             ▼                               ▼
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│  FastEmbed + Qdrant  │   │   Multi-LLM Consensus    │   │  Analytics Engine (DB)   │
│  • 384-dim ONNX      │   │  • Groq LLaMA 3.3 (Critic│   │  • Ebbinghaus Decay      │
│  • Cosine Similarity │   │  • Gemini 1.5 (Multimodal│   │  • Spaced Repetition     │
│  • Syllabus Chunks   │   │  • Key Pool Auto-Rotator │   │  • SQLite + Redis Cache  │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘
```

---

## 💡 Key Engineering Highlights & Interview Talking Points

### 1. FastEmbed ONNX CPU Vectorization vs. Heavy PyTorch Embeddings
* **Problem**: Standard `sentence-transformers` required heavy PyTorch CUDA/CPU libraries (~1.5GB image size and high RAM consumption), leading to cold-start penalties and serverless memory limits.
* **Solution**: Swapped embedding infrastructure to **FastEmbed** (`BAAI/bge-small-en-v1.5`), executing quantized ONNX embeddings directly on CPU. This slashed Docker image size by 70%, lowered memory consumption to <200MB, and reduced query vectorization latency to <15ms.

### 2. High-Availability LLM Ingestion via Key Pool Rotator
* **Problem**: Free-tier Gemini and Groq API keys frequently encounter `HTTP 429 ResourceExhausted` during peak concurrent student sessions.
* **Solution**: Implemented an async-safe **`KeyManager`** that maintains a round-robin rotation across multiple API keys with a 60-second cooldown blacklist on rate limit exceptions, achieving 99.9% uptime during load spikes without dropping in-flight user requests.

### 3. Pedagogical 3-Tier Progressive Hint Enforcement
* **Problem**: Standard LLM tutoring platforms prematurely output full numerical solutions, discouraging student deduction.
* **Solution**: Implemented structured output schemas with Pydantic and regex-based guardrail middleware to gate solutions behind **Tier 1 (Conceptual Nudge)**, **Tier 2 (Structural Strategy & Roadmap)**, and **Tier 3 (Detailed Algebraic Walkthrough)**.

### 4. Cognitive Spaced Repetition Mathematical Engine
* **Mathematical Foundation**: Implemented Ebbinghaus memory stability formulation:
  $$S = (\text{Score} \times \text{Difficulty}) + (0.5 \times \text{Attempts})$$
  $$R(t) = e^{-\frac{t}{S}} \implies \text{Optimal Interval: } I = -S \ln(R_{\text{target}})$$
* **Impact**: Automatically populates dynamic daily study queues and predicts topic retention drop-offs for proactive exam revision.

---

## 🏷️ Skills Taxonomy for ATS Keywords

* **Languages**: Python 3.12, JavaScript (ES6+), SQL, LaTeX, HTML5, CSS3 / Tailwind CSS
* **Frameworks & Libraries**: FastAPI, React.js, Vite, Pydantic v2, SQLAlchemy (Asyncio), LangChain, KaTeX, Lucide React
* **AI & Machine Learning**: Retrieval-Augmented Generation (RAG), Vector Embeddings (FastEmbed / ONNX), Qdrant Vector Database, Large Language Models (LLMs), Prompt Engineering, Multi-Model Consensus, Multimodal Vision OCR
* **Databases & Caching**: Qdrant Cloud, SQLite / aiosqlite, Redis
* **DevOps & Infrastructure**: Docker, Docker Compose, GitHub Actions, CI/CD, Render, Vercel, Uvicorn, WebSockets, REST APIs, CORS Security

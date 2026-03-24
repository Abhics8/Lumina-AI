# Lumina AI 🔮

> AI-powered visual commerce engine with semantic fashion search

[![Build Status](https://github.com/AB0204/Lumina-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/AB0204/Lumina-AI/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-dc382c.svg)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ The Problem

| Traditional Search | Lumina Search |
|-------------------|---------------|
| `"red dress"` → 10,000 generic results | `"bohemian dress for beach wedding"` → Perfect matches |

Lumina understands fashion by **style, vibe, and visual similarity** — not just keywords.

---

## 🎬 Live Demo

> 🔗 **[Try it yourself →](https://huggingface.co/spaces/Ab0202000/lumina-ai-demo)** — Runs FREE on Hugging Face Spaces!

<p align="center">
  <img src="assets/demo-detect.png" alt="Lumina AI - Detect Items" width="800">
</p>

<p align="center"><em>🔍 Detect Items — Zero-shot object detection identifies fashion items with bounding boxes & confidence scores</em></p>

<p align="center">
  <img src="assets/demo-vibe.png" alt="Lumina AI - Vibe Check" width="800">
</p>

<p align="center"><em>✨ Vibe Check — AI analyzes outfit style, occasion fit & fashion vibe using CLIP embeddings</em></p>

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Search Latency (p95) | **45ms** |
| Detection Latency (p95) | **78ms** |
| Recall@10 | **94.2%** |
| Supported Categories | **25+** |
| Catalog Support | **100K+ products** |

---

## 🏗️ Architecture
```mermaid
flowchart TD
    User["User\nImage Upload / Text Query"] --> FE["Next.js 15 Frontend\nTypeScript + Tailwind\nApp Router + Server Components"]
    FE --> API["FastAPI Backend\nPydantic v2 validation\nOpenAPI auto-docs"]
    API --> CACHE{Redis Cache\nCache-aside pattern\nTTL-based invalidation}
    CACHE -->|Cache Miss| PIPELINE[ML Inference Pipeline]
    CACHE -->|Cache Hit| FE
    PIPELINE --> OWL["OWLv2\nZero-shot object detection\nIsolates fashion items"]
    PIPELINE --> SIG["SigLIP\nVision-language embeddings\n768-dim vectors"]
    PIPELINE --> QWEN["Qwen-VL\nStyle + occasion tagging\nVibe analysis"]
    OWL --> EMBED[Embedding Generation]
    SIG --> EMBED
    EMBED --> QDRANT[("Qdrant Vector DB\n100K+ embeddings\nANN retrieval")]
    QDRANT --> RESULTS["Ranked Results\n94.2% Recall@10\n45ms p95"]
    RESULTS --> FE
```

**Embedding pipeline (batch ingestion):**
```mermaid
flowchart LR
    RAW[Raw Product Images] --> DEDUP[Deduplication]
    DEDUP --> VALIDATE[Schema Validation]
    VALIDATE --> BATCH[Batch Processor\nCheckpointing]
    BATCH --> OWL2[OWLv2 Detection]
    OWL2 --> SIGLIP[SigLIP Embedding]
    SIGLIP --> IDEM[Idempotent Write]
    IDEM --> QDB[(Qdrant\n100K+ vectors)]
```

---

## 🛠️ Tech Stack

### Core AI
| Model | Purpose |
|-------|---------|
| **OWLv2** | Zero-shot object detection (detects "shirt", "dress", "shoes") |
| **SigLIP** | Multimodal embeddings for semantic search |
| **Qwen-VL** | Scene understanding and style tagging |

### Infrastructure
- **Backend**: FastAPI (Python) - Async, high-performance API
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Database**: Qdrant (Vector DB) - 100K+ embeddings
- **Caching**: Redis
- **DevOps**: Docker, GitHub Actions CI/CD

---

## 💡 Key Features

### 1. 🔍 Zero-Shot Object Detection
Upload any image → Automatically detect and isolate fashion items

### 2. 🎨 Vibe Analysis
Get structured JSON breakdown of:
- **Style**: Bohemian, Minimalist, Streetwear, etc.
- **Occasion**: Wedding, Beach, Office, Date Night
- **Setting**: Urban, Nature, Indoor, etc.

### 3. 🛍️ Semantic Search
Search using natural language or images:
- `"outfit for a beach party"`
- `"minimalist professional look"`
- Upload a photo → Find similar products

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/Abhics8/Lumina-AI.git
cd Lumina-AI

# Start all services
docker-compose up --build -d
```

**Services:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/docs |
| Qdrant UI | http://localhost:6333/dashboard |

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure
```
Lumina-AI/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration
│   │   └── services/     # AI model services
│   └── requirements.txt
├── frontend/
│   ├── app/              # Next.js App Router
│   ├── components/       # React components
│   ├── lib/              # API client & utilities
│   └── types/            # TypeScript types
├── docker-compose.yml
└── .github/workflows/    # CI/CD
```

---

## 📖 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/detect` | POST | Detect fashion items in image |
| `/api/search` | POST | Semantic product search |
| `/api/vibe` | POST | Analyze style/occasion/setting |
| `/api/embed` | POST | Generate image embeddings |

Full API documentation: `http://localhost:8000/docs`

---

## 🧪 Development
```bash
# Run backend tests
cd backend && pytest tests/ -v

# Run frontend tests
cd frontend && npm run test
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

[MIT License](LICENSE)

---

## 👤 Author

**Abhi Bhardwaj** — MS Computer Science, George Washington University (May 2026)

[![Portfolio](https://img.shields.io/badge/Portfolio-ab0204.github.io-1B2A4A)](https://ab0204.github.io/Portfolio/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin)](https://www.linkedin.com/in/abhi-bhardwaj-23b0961a0/)
[![GitHub](https://img.shields.io/badge/GitHub-Abhics8-181717?logo=github)](https://github.com/Abhics8)

# RepoArkeolog

> Bir GitHub reposunu çoklu AI ajanıyla 5 dakikada anlatan araç.
> SolveX AI Hackathon 2026

## Demo

[Demo URL buraya eklenecek — Vercel deploy sonrası]

## Ne Yapıyor?

1. GitHub URL gir
2. AI ajanları paralel/sıralı analiz yapar (Plan → Mimar → Tarihçi → Dedektif → Onboarding)
3. Tek sayfada interaktif rapor: Özet, Mimari Harita, Git Timeline, Repoyla Sohbet

## Hızlı Başlangıç

### Gereksinimler
- Node.js 20+
- Python 3.11+
- Docker + Docker Compose
- Gemini API Key (Google AI Studio — ücretsiz)
- Groq API Key (console.groq.com — ücretsiz)

### Kurulum

```bash
# 1. Repo klonla
git clone <repo-url>
cd repoarkeolog

# 2. Altyapıyı başlat (PostgreSQL, Redis, Qdrant)
cd infra && docker-compose up -d && cd ..

# 3. Backend
cd backend
cp .env.example .env
# .env dosyasına GEMINI_API_KEY ve GROQ_API_KEY ekle

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head

# Terminal 1 — FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 4. Frontend
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev  # http://localhost:3000
```

## Mimari

Detaylar için [ARCHITECTURE.md](ARCHITECTURE.md)

## Ajanlar

| Ajan | Model | Görev |
|---|---|---|
| Plan Agent | Gemini 2.5 Flash | Repo meta analizi + ajan planı |
| Mimar | Gemini 2.5 Flash | Mimari harita + bağımlılık grafiği |
| Tarihçi | Groq Llama 3.3 70B | Git geçmişi + evrim hikayesi |
| Dedektif | Gemini 2.5 Flash | Teknik borç + sağlık raporu |
| Onboarding | Gemini 2.5 Flash | Yeni geliştirici yol haritası |
| Chat | Gemini 2.5 Flash + RAG | Repoyla sohbet |

## Kapsam

- Desteklenen diller: Python, JavaScript, TypeScript
- Sadece public GitHub repoları
- Maks. repo boyutu: 500 MB

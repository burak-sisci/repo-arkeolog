# RepoArkeolog

> Bir GitHub reposunu çoklu AI ajanıyla 5 dakikada anlatan araç.
> **SolveX AI Hackathon 2026 — 2.'lik ödülü 🏆**

[![SolveX 2026](https://img.shields.io/badge/SolveX-Hackathon%202026-6366f1)](https://nocodearea.com/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](#)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2014-000000)](#)
[![LLM](https://img.shields.io/badge/LLM-Cerebras%20qwen--3--235B-ff6b35)](#)
[![Python](https://img.shields.io/badge/Python-3.11--3.12-3776ab)](#)

🔗 **Canlı:** https://frontend-production-9e092.up.railway.app/

---

## Takım

| Rol | Üye | GitHub |
|-----|-----|--------|
| Lead Developer / Maintainer | burak-sisci | [@burak-sisci](https://github.com/burak-sisci) |
| Feature Developer | eminehatundincer | [@eminehatundincer](https://github.com/eminehatundincer) |
| Feature Developer | Serifenurr | [@Serifenurr](https://github.com/Serifenurr) |

Geliştirme süreci [`CONTRIBUTING.md`](CONTRIBUTING.md) ve [`AI_USAGE.md`](AI_USAGE.md) dosyalarındaki şartname uyumlu kurallara göre yürütülür.

---

## Ne Yapıyor?

1. GitHub URL gir.
2. 5 AI ajan repoyu sırayla analiz eder: **Plan → Mimar → Tarihçi → Dedektif → Onboarding**.
3. Tek sayfada interaktif rapor: **Özet, Mimari Harita, Timeline, Repoyla Konuş**.

### Öne Çıkan Özellikler

- **11 dil desteği** (tree-sitter): Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Ruby, PHP
- **Zenginleştirilmiş Mimari Harita** — rol sınıflandırması, döngü tespiti (Tarjan SCC), klasör grupları, 4 farklı layout, PNG dışa aktarma
- **Smart Clone** — `--depth 50` + `--filter=blob:limit=1m`, büyük binary/LFS atlanır, 4 kademeli fallback
- **Default branch otomatik tespit** — `main`/`master`/`develop` fark etmez (GitHub API)
- **Karanlık tema** + FOUC-engelleyen başlatma (inline script)
- **WebSocket ile canlı ilerleme** (Redis pub/sub)
- **PostgreSQL cache** — aynı repo+branch için tekrar analiz yapılmaz (`sha256(url:branch)`)
- **2 GB tavan repo boyutu** + ≤5000 chunk sınırı (LLM prompt patlamasına karşı)
- **Dayanıklı LLM çağrısı** — 240 sn timeout, transient hata (429/500/502/503/504/timeout/overloaded) için üstel backoff
- **Sağlık rozeti & kullanım göstergesi** — `/api/health`, `/api/usage` ile canlı durum

---

## Mimari (Özet)

```
Next.js (frontend) ──► FastAPI (REST + WS) ──► Celery worker (--pool=solo)
                                  │                  │
                                  ├── PostgreSQL (cache + sonuçlar)
                                  ├── Redis (broker + pub/sub)
                                  ├── Qdrant (opsiyonel — chat/RAG)
                                  └── Cerebras qwen-3-235b (5 ajan)
                                  └── Gemini (embedding + chat stream, ops.)
```

Detaylar: [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Ajanlar

| Ajan | Görev | LLM |
|------|-------|-----|
| **Plan Agent** | Repo metadata → ajan planı + alt görevler | Cerebras qwen-3-235b |
| **Mimar** | Klasör ağacı + import grafı → mimari harita & modül özetleri | Cerebras qwen-3-235b |
| **Tarihçi** | Git geçmişi (akıllı commit seçimi) → evrim hikayesi, milestone, hot files | Cerebras qwen-3-235b |
| **Dedektif** | Lint (ruff/eslint) + vulture + TODO + bağımlılık manifestleri → sağlık karnesi | Cerebras qwen-3-235b |
| **Onboarding** | Diğer 3 ajan + plan sentezi → ilk hafta yol haritası | Cerebras qwen-3-235b |

Tümü Cerebras `qwen-3-235b-a22b-instruct-2507` üzerinde çalışır.
Chat/RAG ayrı bir hat: **Gemini `gemini-embedding-001`** (768 boyut) + **`gemini-2.5-flash`** streaming. Qdrant veya `GEMINI_API_KEY` boşsa chat sessizce devre dışı kalır, diğer ajanlar çalışmaya devam eder.

---

## Hızlı Başlangıç

### Gereksinimler

- Node.js 20+
- Python **3.11–3.12** (`pyproject.toml` `requires-python = ">=3.11,<3.13"`)
- PostgreSQL 16+ (yerel servis ya da `infra/docker-compose.yml`)
- Redis 7
- Qdrant *(opsiyonel — chat/RAG için)*
- **Cerebras API key** ([cloud.cerebras.ai](https://cloud.cerebras.ai))
- *(Opsiyonel)* Gemini API key — chat aktif olsun istersen

### Kurulum

```bash
git clone https://github.com/burak-sisci/repo-arkeolog.git
cd repo-arkeolog

# 1) Altyapı (postgres + redis + qdrant) — Docker kullanıyorsan
cd infra && docker compose up -d && cd ..

# 2) Backend
cd backend
cp .env.example .env
# .env içine en azından CEREBRAS_API_KEY ekle
python -m venv .venv
.venv\Scripts\activate          # Windows; Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# Terminal 1 — FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker (Windows için --pool=solo şart)
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# 3) Frontend (yeni terminal)
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev    # http://localhost:3000
```

### Ortam Değişkenleri

`backend/.env.example` ve `frontend/.env.local.example` örnek olarak versiyon kontrol altında. Sadece `CEREBRAS_API_KEY` zorunludur; `GEMINI_API_KEY` ve `QDRANT_URL` boş kalırsa chat/RAG sessizce devre dışı kalır.

---

## Deploy

Tek Railway projesi içinde 5 servis: **postgres, redis, backend, worker, frontend**. Detaylı rehber: [`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md).

---

## AI-Augmented Development

Şartname §5 uyarınca **Plan Agent** ve **Skills Agent** süreç boyunca aktif olarak kullanıldı:

- Plan Agent çıktıları: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md)
- Skills Agent etkileşimleri ve refactor geçmişi: [`AI_USAGE.md`](AI_USAGE.md)
- Kod dosyalarında `# AI:` / `// AI:` etiketleri AI yardım noktalarını işaretler.

---

## Katkı

PR açmadan önce [`CONTRIBUTING.md`](CONTRIBUTING.md) bölümünü oku — branch isimlendirme, commit formatı, PR şablonu (AI Traceability bölümü zorunlu) burada.

---

## Lisans

MIT — bkz. [`LICENSE`](LICENSE) *(eklenecek)*.

# RepoArkeolog

> Bir GitHub reposunu çoklu AI ajanıyla 5 dakikada anlatan araç.
> **SolveX AI Hackathon 2026**

[![SolveX 2026](https://img.shields.io/badge/SolveX-Hackathon%202026-6366f1)](https://nocodearea.com/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](#)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2014-000000)](#)
[![LLM](https://img.shields.io/badge/LLM-Cerebras%20qwen--3--235B-ff6b35)](#)

---

## Takım

| Rol | Üye | GitHub |
|-----|-----|--------|
| Lead Developer / Maintainer | burak-sisci | [@burak-sisci](https://github.com/burak-sisci) |
| Feature Developer | eminehatundincer | [@eminehatundincer](https://github.com/eminehatundincer) |
| Feature Developer | Serifenurr | [@Serifenurr](https://github.com/Serifenurr) |

Geliştirme süreci [`CONTRIBUTING.md`](CONTRIBUTING.md) ve [`AI_USAGE.md`](AI_USAGE.md) dosyalarındaki şartname uyumlu kurallara göre yürütülür.

---

## Demo

> Canlı URL: *Railway deploy sonrası eklenecek.*

---

## Ne Yapıyor?

1. GitHub URL gir.
2. 5 AI ajan repoyu paralel/sıralı analiz eder: **Plan → Mimar → Tarihçi → Dedektif → Onboarding**.
3. Tek sayfada interaktif rapor: **Özet, Mimari Harita, Git Timeline, Repoyla Sohbet**.

### Öne Çıkan Özellikler

- **11 dil desteği** (tree-sitter): Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Ruby, PHP
- **Zenginleştirilmiş Mimari Harita** — rol sınıflandırması, döngü tespiti (Tarjan SCC), klasör grupları, 4 farklı layout, PNG dışa aktarma
- **Smart Clone** — `--depth 50` + `--filter=blob:limit=1m`, büyük binary/LFS atlanır
- **Default branch otomatik tespit** — `main`/`master`/`develop` fark etmez
- **Karanlık tema** + FOUC-engelleyen başlatma
- **WebSocket ile canlı ilerleme**
- **PostgreSQL cache** — aynı repo+branch için tekrar analiz yapılmaz

---

## Mimari (Özet)

```
Next.js (frontend) ──► FastAPI (REST + WS) ──► Celery worker
                                  │                  │
                                  ├── PostgreSQL (cache + sonuçlar)
                                  ├── Redis (broker + pub/sub)
                                  └── Cerebras qwen-3-235b (5 ajan)
```

Detaylar: [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Ajanlar

| Ajan | Görev |
|------|-------|
| **Plan Agent** | Repo metadata → ajan planı + alt görevler |
| **Mimar** | İmport grafiği + klasör yapısı → mimari harita |
| **Tarihçi** | Git geçmişi → evrim hikayesi (milestone seçimi + hot files) |
| **Dedektif** | Static analiz + TODO + bağımlılık → sağlık raporu |
| **Onboarding** | 3 ajan sentezi → ilk hafta yol haritası |

Tümü Cerebras `qwen-3-235b-a22b-instruct-2507` üzerinde çalışır.

---

## Hızlı Başlangıç

### Gereksinimler
- Node.js 20+
- Python 3.11+ (3.14 ile de test edildi)
- PostgreSQL 17 (lokal servis)
- Redis 7 (lokal servis)
- Qdrant binary *(opsiyonel — chat/RAG için)*
- **Cerebras API key** ([cloud.cerebras.ai](https://cloud.cerebras.ai))

### Kurulum

```bash
git clone https://github.com/burak-sisci/repo-arkeolog.git
cd repo-arkeolog

# Backend
cd backend
cp .env.example .env
# .env içine CEREBRAS_API_KEY ekle
python -m venv .venv
.venv\Scripts\activate          # Windows; Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# Terminal 1 — FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# Frontend (yeni terminal)
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev    # http://localhost:3000
```

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

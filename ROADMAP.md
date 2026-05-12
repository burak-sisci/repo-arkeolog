# RepoArkeolog — ROADMAP

> Bu dosya **Plan Agent** tarafından üretilir ve sub-task'ları AI ajanları belirler (şartname §5.2). Manuel değişiklikler PR + Code Review üzerinden yapılır.

---

## MVP — Hackathon Demo *(tamamlandı)*

### Altyapı
- [x] PostgreSQL 16+ kurulumu *(yerel servis veya `infra/docker-compose.yml`)*
- [x] Redis 7 *(yerel)*
- [x] Qdrant binary/Docker *(yerel — opsiyonel)*
- [x] Backend Python 3.11–3.12 venv + paketler
- [x] `infra/docker-compose.yml` ile postgres + redis + qdrant tek komutla

### Backend
- [x] FastAPI iskeleti + env-driven CORS
- [x] Alembic migrations *(001_initial)*
- [x] Celery worker + Redis broker *(`--pool=solo`)*
- [x] WebSocket progress yayını *(Redis pub/sub)*
- [x] Smart git clone *(depth 50 + blob:limit + single-branch + 4 kademeli fallback)*
- [x] 11 dilli tree-sitter chunklayıcı *(lazy parser cache)*
- [x] **Plan Agent** *(Cerebras qwen-3-235b)*
- [x] **Mimar Agent** + Python/JS/TS import regex graf üretimi
- [x] **Tarihçi Agent** *(akıllı commit seçimi + hot files)*
- [x] **Dedektif Agent** *(ruff/eslint/vulture + TODO + 9 paket yöneticisi manifesti)*
- [x] **Onboarding Agent** *(3 ajan + plan sentezi)*
- [x] LLM retry/throttle katmanı *(Cerebras 240s timeout + 5 retry; Gemini 8 retry + 13s throttle)*
- [x] GitHub default branch otomatik tespiti
- [x] Cache *(repo_hash = sha256(url:branch))*
- [x] 2 GB hard limit + 5000 chunk üst sınırı
- [x] `/api/health`, `/api/usage` endpoint'leri
- [x] Chat/RAG hattı *(Gemini embedding + streaming, opsiyonel)*

### Frontend
- [x] Landing page + URL girişi + 3 demo butonu + tema toggle
- [x] Analiz sayfası iskeleti + sekmeler (Özet / Mimari Harita / Timeline / Repoyla Konuş)
- [x] **ProgressBar** *(WebSocket)*
- [x] **SummaryTab**
- [x] **MimapTab v1** *(Cytoscape + concentric)*
- [x] **MimapTab v2 zenginleştirme** — rol sınıfı (8 rol), Tarjan SCC döngü tespiti, 4 layout, klasör grupları, neighbor listesi, PNG dışa aktarma
- [x] **TimelineTab** *(vis-timeline)*
- [x] **ChatTab** *(SSE streaming UI — backend Gemini RAG'a bağlı, ops.)*
- [x] **Karanlık tema** *(class-based + FOUC engelleyici inline script)*
- [x] **HealthBadge** + **UsageStatusDot** *(canlı kullanım göstergesi)*

### Şartname Uyumu
- [x] `CONTRIBUTING.md` *(branch / commit / PR kuralları)*
- [x] `AI_USAGE.md` *(Plan + Skills Agent kayıtları)*
- [x] `.github/PULL_REQUEST_TEMPLATE.md` *(AI Traceability zorunlu)*
- [x] `.github/ISSUE_TEMPLATE/feature.md`, `bug.md`, `config.yml`
- [x] README takım rolleri + AI usage section
- [ ] Branch protection *(GitHub UI üzerinden — manuel ayar gerekir)*
- [ ] AI Traceability `# AI:` / `// AI:` etiketleri kritik dosyalarda

---

## Sıradaki — Canlıya Alma *(tamamlandı)*

### Railway Deploy
- [x] `backend/Dockerfile` (python:3.11-slim + start-web.sh + start-worker.sh)
- [x] `frontend/Dockerfile` (Next.js standalone build, node:20-alpine, non-root user)
- [x] Servis tanımları: postgres + redis + backend + worker + frontend (5 servis)
- [x] CORS env-driven (`CORS_ORIGINS`)
- [x] Embedder no-op fallback *(`QDRANT_URL` veya `GEMINI_API_KEY` boşsa chat sessizce kapanır)*
- [x] Alembic auto-migrate (`start-web.sh` içinde)
- [x] Python 3.11 pin
- [x] `.env.example` & `.env.local.example` güncel
- [x] Postgres + Redis add-on
- [x] WebSocket prod konfigürasyonu (`--proxy-headers`)
- [x] **Canlı:** https://frontend-production-9e092.up.railway.app/

### Final Review *(şartname §6 — tamamlandı)*
- [x] Tüm kod Cerebras qwen-3-235b ile refactor taraması
- [x] Performans optimizasyonu raporu
- [x] Güvenlik kontrol listesi *(secrets, CORS, Next.js CVE yamaları)*
- [x] Md dokümantasyonun kod tabanıyla hizalanması

---

## Stretch Goals *(post-hackathon)*

- [ ] Chat aktivasyonu için sentence-transformers lokal embedding seçeneği *(Gemini gerektirmesin)*
- [ ] Mini-map / overview navigatör (Cytoscape)
- [ ] Mimar: cyclomatic complexity skoru
- [ ] Dedektif: Bandit + semgrep entegrasyonu
- [ ] Auth + analiz geçmişi
- [ ] İki repo karşılaştırma görünümü
- [ ] CI: GitHub Actions ile lint + test
- [ ] Mobil ekran responsive iyileştirmeleri
- [ ] Public repo dışında token ile private repo desteği

# RepoArkeolog — ROADMAP

> Bu dosya **Plan Agent** tarafından üretilir ve sub-task'ları AI ajanları belirler (şartname §5.2). Manuel değişiklikler PR + Code Review üzerinden yapılır.

---

## MVP — Hackathon Demo *(tamamlandı)*

### Altyapı
- [x] Postgres 17 kurulumu *(yerel servis)*
- [x] Redis 7 *(yerel)*
- [x] Qdrant binary *(yerel — opsiyonel)*
- [x] Backend Python 3.14 venv + paketler

### Backend
- [x] FastAPI iskeleti + CORS
- [x] Alembic migrations
- [x] Celery worker + Redis broker
- [x] WebSocket progress yayını
- [x] Smart git clone *(depth 50 + blob:limit)*
- [x] 11 dilli tree-sitter chunklayıcı
- [x] **Plan Agent** *(Cerebras qwen-3-235b)*
- [x] **Mimar Agent** + import regex graf üretimi
- [x] **Tarihçi Agent** *(commit istatistikleri + milestone seçimi)*
- [x] **Dedektif Agent** *(ruff/eslint + TODO + manifest)*
- [x] **Onboarding Agent** *(3 ajan sentezi)*
- [x] LLM retry/throttle katmanı *(429, 503, timeout)*
- [x] GitHub default branch otomatik tespiti
- [x] 4 kademeli klon fallback

### Frontend
- [x] Landing page + URL girişi
- [x] Analiz sayfası iskeleti + sekmeler
- [x] **ProgressBar** *(WebSocket)*
- [x] **SummaryTab**
- [x] **MimapTab** v1 *(Cytoscape + concentric)*
- [x] **MimapTab v2 zenginleştirme** — rol sınıfı, döngü tespiti, 4 layout, klasör grupları, neighbor listesi, PNG dışa aktarma
- [x] **TimelineTab** *(vis-timeline)*
- [x] **ChatTab** UI *(backend RAG kapalı)*
- [x] **Karanlık tema** *(class-based + FOUC engelleyici)*
- [x] HealthBadge

### Şartname Uyumu
- [x] `CONTRIBUTING.md` *(branch / commit / PR kuralları)*
- [x] `AI_USAGE.md` *(Plan + Skills Agent kayıtları)*
- [x] `.github/PULL_REQUEST_TEMPLATE.md` *(AI Traceability zorunlu)*
- [x] `.github/ISSUE_TEMPLATE/feature.md`, `bug.md`
- [x] README takım rolleri + AI usage section
- [ ] Branch protection *(GitHub UI üzerinden)*
- [ ] AI Traceability header'ları kritik dosyalarda

---

## Sıradaki — Canlıya Alma

### Railway Deploy
- [ ] `Dockerfile` (backend)
- [ ] `Dockerfile` veya buildpack (frontend)
- [ ] `railway.toml` veya servis tanımları
- [ ] CORS env-driven (`CORS_ORIGINS`)
- [ ] Embedder no-op fallback *(Qdrant URL boşsa)*
- [ ] Alembic auto-migrate (start command'da)
- [ ] Python 3.11 pin
- [ ] `.env.example` güncelle
- [ ] Postgres + Redis add-on
- [ ] WebSocket prod konfigürasyonu

### Final Review *(şartname §6)*
- [ ] Tüm kod Cerebras qwen-3-235b ile refactor taraması
- [ ] Performans optimizasyonu raporu
- [ ] Güvenlik kontrol listesi *(secrets, CORS, rate limit, SQL injection)*

---

## Stretch Goals

- [ ] Chat aktivasyonu *(lokal sentence-transformers veya OpenAI embed)*
- [ ] Mini-map / overview navigatör (Cytoscape)
- [ ] Mimar: cyclo'mantic complexity skoru
- [ ] Dedektif: Bandit + semgrep entegrasyonu
- [ ] Auth + analiz geçmişi
- [ ] İki repo karşılaştırma görünümü
- [ ] CI: GitHub Actions ile lint + test
- [ ] Mobil ekran responsive iyileştirmeleri

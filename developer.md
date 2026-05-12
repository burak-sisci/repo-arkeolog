# RepoArkeolog — Geliştirici Dokümanı

> **Proje:** SolveX AI Hackathon 2026 — RepoArkeolog (2.'lik 🏆)
> **Hedef:** Bir GitHub reposunu çoklu AI ajanıyla "kazıyıp" yeni gelen geliştiriciye dakikalar içinde anlatan araç.
> **Canlı:** https://frontend-production-9e092.up.railway.app/
> **Desteklenen diller (tree-sitter):** Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Ruby, PHP
> **Çalışma zamanı LLM:** 5 ajanın tamamı **Cerebras `qwen-3-235b-a22b-instruct-2507`**; chat/RAG **Gemini** üzerinde *(opsiyonel)*.

---

## İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Sistem Mimarisi](#2-sistem-mimarisi)
3. [Akışlar](#3-akışlar)
4. [Teknoloji Yığını](#4-teknoloji-yığını)
5. [Veri Modelleri](#5-veri-modelleri)
6. [API Sözleşmesi](#6-api-sözleşmesi)
7. [Klasör Yapısı](#7-klasör-yapısı)
8. [Ajan İmplementasyonları](#8-ajan-i̇mplementasyonları)
9. [Frontend Notları](#9-frontend-notları)
10. [GitHub Akışı](#10-github-akışı)
11. [Kurulum ve Çalıştırma](#11-kurulum-ve-çalıştırma)
12. [Deploy](#12-deploy)
13. [Risk ve Sorun Giderme](#13-risk-ve-sorun-giderme)

---

## 1. Proje Özeti

### 1.1. Ne Yapıyoruz?

RepoArkeolog, kullanıcıdan bir **GitHub repository URL'si** alır ve birden fazla AI ajanını sıralı çalıştırarak repoyu **dakikalar içinde analiz eder**. Çıktı, tek sayfalı interaktif bir webdir; içinde:

- **Özet rapor** (proje ne, ne işe yarar, sağlık durumu, onboarding kılavuzu)
- **Gezinilebilir mimari haritası** (tıklanabilir bağımlılık grafiği, rol sınıflandırması, döngü tespiti, 4 layout)
- **Zaman çizelgesi** (akıllı seçilmiş commit'lerden milestone'lar + hot files + contributor özeti)
- **Repoyla sohbet** (RAG tabanlı soru-cevap — Qdrant + Gemini'ye bağlı; opsiyonel)

### 1.2. Neden?

Yeni geliştiricinin bir projeye alışması ortalama 1–2 hafta sürer. RepoArkeolog bu süreci AI ajanlarına devrederek dakikalara indirir.

### 1.3. Şartname Uyumu

Şartname iki yapı istiyor:
1. **Plan Agent** — projenin mimari planını çıkaran üst akıl
2. **Skills Agent** — uzmanlık alanlarında çalışan ajanlar

Bizim mimarimiz bu yapıyı hem **geliştirme sürecinde** (Plan + Skills Agent ile yazıldı) hem de **ürünün kendisi** olarak somutlaştırır.

### 1.4. Kapsam Sınırları

| Konu | Karar |
|---|---|
| **Desteklenen diller** | 11 dil (tree-sitter). Dosya bazlı: chunker hangi uzantıyı tanırsa o işlenir. Tanınmayan dilde tüm dosya tek `module` chunk olur. |
| **Auth / kullanıcı sistemi** | Yok. Demo modu — herkes URL girip analiz başlatabilir. |
| **Private repo desteği** | Yok. Sadece public GitHub repoları. Private gelirse 401. |
| **Repo boyutu** | Üst sınır **2048 MB** (2 GB). Üzeri 413 hatası. |
| **Chunk sayısı** | LLM prompt patlamasına karşı **≤5000 chunk** (sınıf > fonksiyon > modül önceliği). |
| **Commit örnekleme** | 150 commit üzeri repolarda akıllı seçim (ilk 10 + son 30 + merge'ler + top-%20 büyük diff + aylık). |

---

## 2. Sistem Mimarisi

Üst düzey diyagram için [`ARCHITECTURE.md`](ARCHITECTURE.md) dosyasına bak. Kısaca:

```
KULLANICI → Next.js 14 → FastAPI (REST + WebSocket) → Celery worker
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
        PostgreSQL                   Redis                     Cerebras
        (cache,                  (broker +                  qwen-3-235b
        sonuçlar)                pub/sub)                   (5 ajan)
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                          Qdrant (ops.)        Gemini (ops.)
                          chat vektörleri      embed + chat
```

### Mimari Prensipler

- **Asenkron:** Analiz 1–5 dk. Celery + WebSocket non-blocking. Worker `--pool=solo` (Windows + iç içe asyncio uyumluluğu).
- **Modüler ajanlar:** `BaseAgent` arayüzü. Yeni ajan = yeni dosya.
- **Fail-soft:** Bir ajan çökerse pipeline durmaz; alan `{"error": "...", "status": "failed"}` olarak kaydedilir, kullanıcı diğer ajanların sonucunu görür.
- **Cache-first:** `repo_hash = sha256(url:branch).hexdigest()`. Aynı repo+branch tekrar analiz edilmez.
- **Token tasarrufu:** Ajanlara ham kod yerine **metadata + plan + chunk özeti** gider.
- **Dayanıklı LLM:** Cerebras 240 sn timeout + 5 retry; Gemini 8 retry + 13 sn istek-arası throttle.

---

## 3. Akışlar

### 3.1. Ana Analiz Akışı

1. Frontend `POST /api/analyze` → backend doğrular (URL regex + GitHub API `validate_repo_url`).
2. Private/404/413 erken döner. Default branch GitHub API'den çekilir.
3. Cache hit varsa direkt mevcut analysis_id döner.
4. Aksi halde yeni `Analysis` kaydı + Celery task (`analyze_repo_task.delay`).
5. Frontend WebSocket `/ws/progress/{id}` + 3 sn'lik polling `GET /api/analysis/{id}` ile durumu izler.
6. Worker pipeline'ı sırayla çalıştırır ve her aşamada Redis `progress:{id}` kanalına yayın yapar.
7. Tamamlanınca `status = done`, sonuçlar JSON kolonlarda saklanır.

### 3.2. Chat (RAG) Akışı

1. `POST /api/chat/{id}` — kullanıcı mesajı.
2. `app.rag.retriever.retrieve_chunks` — Gemini ile sorgu embed → Qdrant `search` top 8 → dosya yolu boost → top 5.
3. Context oluşturulur: kod chunk'ları + mimar/dedektif çıktısından sorgu kelimeleriyle eşleşen alt küme.
4. Gemini `gemini-2.5-flash` streaming → SSE event akışı (`sources`, `chunk`, `done`).
5. Kullanıcı ve asistan mesajları `chat_messages` tablosuna kaydedilir.

`QDRANT_URL` veya `GEMINI_API_KEY` boşsa retriever boş liste döner ve chat sessizce kapanır.

### 3.3. Hata Davranışları

| Durum | HTTP / Davranış |
|---|---|
| Geçersiz URL | 400 |
| Repo bulunamadı | 404 |
| Private repo | 401 ("demo modunda yalnızca public repo destekleniyor") |
| Repo > 2 GB | 413 |
| Analiz bitmeden chat | 400 ("analiz henüz tamamlanmadı") |
| Bir Skill ajan exception | `<field>_output = {"error": "...", "status": "failed"}`, pipeline devam eder |
| LLM transient (429/5xx/timeout) | Üstel backoff (Cerebras 5x, Gemini 8x) |
| Aynı repo+branch yeniden | Cache hit, `cached: true` döner |

---

## 4. Teknoloji Yığını

### 4.1. Frontend

| Teknoloji | Versiyon | Neden |
|---|---|---|
| Next.js | 14.2.35 | App Router, SSR, CVE yamaları |
| TypeScript | 5.x | Type safety |
| TailwindCSS | 3.x | Hızlı styling + `darkMode: "class"` |
| @radix-ui/react-dialog, react-tabs | 1.x | Erişilebilir primitive'ler |
| Cytoscape.js + cytoscape-dagre + dagre | 3.29 / 2.5 / 0.8 | Mimari graf — 4 layout |
| vis-timeline | 7.7 | Git timeline |
| ai (Vercel AI SDK) | 3.2 | Chat streaming yardımcıları |
| socket.io-client | 4.7 | (içeride native `WebSocket` kullanılıyor; SDK gelecek geliştirme için hazır) |
| react-syntax-highlighter | 15.5 | Chat'te kod gösterimi |
| lucide-react | 0.395 | İkonlar |

### 4.2. Backend

| Teknoloji | Versiyon (pin) | Neden |
|---|---|---|
| Python | 3.11–3.12 (`>=3.11,<3.13`) | tree-sitter ABI + paket uyumu |
| FastAPI | ≥0.111 | Async + OpenAPI + Pydantic v2 |
| Pydantic | ≥2.7 + pydantic-settings | Validation + env config |
| Celery | ≥5.4 | Task queue (`--pool=solo`) |
| Redis | ≥5.0 + `redis.asyncio` | Broker + pub/sub |
| SQLAlchemy | ≥2.0 + Alembic | ORM + migrations |
| psycopg2-binary | ≥2.9 | Postgres driver |
| GitPython | ≥3.1 | Klonlama + git log |
| tree-sitter + 11 dil grameri | ≥0.22 / 0.23 | AST parse |
| httpx | ≥0.27 | GitHub API + webhook |
| ruff, vulture, radon | — | Static analiz |

### 4.3. AI Katmanı

| Servis | Model | Görev | Zorunlu? |
|---|---|---|---|
| Cerebras Inference | `qwen-3-235b-a22b-instruct-2507` | 5 ajanın tamamı | **Evet** |
| Gemini | `gemini-2.5-flash` | Chat streaming (RAG) | Hayır (boşsa chat kapanır) |
| Gemini | `gemini-embedding-001` (768 dim) | Kod chunk embedding | Hayır |
| Qdrant | self-hosted | Vektör DB | Hayır |
| Groq | `llama-3.3-70b-versatile` | İstemci kodda mevcut, ajanlar şu an kullanmıyor | Hayır |

### 4.4. Deploy

| Bileşen | Yer | Imaj / Komut |
|---|---|---|
| Frontend | Railway | `frontend/Dockerfile` — Next.js standalone, node:20-alpine |
| Backend API | Railway | `backend/Dockerfile` + `start-web.sh` |
| Worker | Railway | aynı imaj + `start-worker.sh` (`--pool=solo`) |
| Postgres | Railway add-on | otomatik |
| Redis | Railway add-on | otomatik |
| Qdrant | (opsiyonel) | Qdrant Cloud free tier veya yerel Docker |

---

## 5. Veri Modelleri

### 5.1. PostgreSQL Şeması *(SQLAlchemy 2.x Mapped API — `backend/app/models.py`)*

```python
class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_url: Mapped[str] = mapped_column(String(500), index=True)
    repo_hash: Mapped[str] = mapped_column(String(64), index=True)  # cache key
    commit_sha: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|failed
    progress: Mapped[dict] = mapped_column(JSON, default=dict)

    plan_output: Mapped[dict | None] = mapped_column(JSON)
    mimar_output: Mapped[dict | None] = mapped_column(JSON)
    tarihci_output: Mapped[dict | None] = mapped_column(JSON)
    dedektif_output: Mapped[dict | None] = mapped_column(JSON)
    onboarding_output: Mapped[dict | None] = mapped_column(JSON)

    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

İlk migration: `backend/alembic/versions/001_initial.py`.

### 5.2. Qdrant Koleksiyon Şeması

Her analiz için koleksiyon adı: `repo_{analysis_id}`. Vektör boyutu **768** (`gemini-embedding-001`), distance **COSINE**.

Payload alanları: `file_path`, `start_line`, `end_line`, `chunk_type` (function/class/module), `name`, `language`, `code` (≤4000 char).

### 5.3. Pydantic Şemaları *(`backend/app/schemas.py`)*

`AnalyzeRequest`, `AnalyzeResponse` (`cached: bool`), `ProgressUpdate`, `AnalysisResult`, `ChatRequest`, `ChatResponse`, `UsageStatus`. Repo URL plain string olarak alınır (HttpUrl validasyonu kullanılmıyor — GitHub API ile doğrulanıyor).

---

## 6. API Sözleşmesi

### REST

#### `POST /api/analyze` → 202

```json
{ "repo_url": "https://github.com/foo/bar", "branch": "main" }
```

```json
{ "analysis_id": "uuid", "status": "pending", "cached": false }
```

Hatalar: 400 (geçersiz URL), 401 (private), 404 (bulunamadı), 413 (>2 GB).

#### `GET /api/analysis/{id}` → 200

```json
{
  "analysis_id": "uuid",
  "status": "done",
  "repo_url": "...",
  "progress": {},
  "results": {
    "summary": { /* plan_output */ },
    "architecture_graph": { "nodes": [...], "edges": [...] },
    "mimar": { /* mimar_output */ },
    "timeline": { /* tarihci_output */ },
    "health_report": { /* dedektif_output */ },
    "onboarding_guide": { /* onboarding_output */ }
  },
  "error": null,
  "created_at": "...",
  "completed_at": "..."
}
```

#### `POST /api/chat/{id}` — SSE

```
data: {"type":"sources","sources":[{"file":"auth/login.py","lines":"42-87","name":"authenticate"}]}
data: {"type":"chunk","content":"Auth sistemi "}
data: {"type":"chunk","content":"JWT tabanlı..."}
data: {"type":"done"}
```

#### `GET /api/health` → `{"status":"ok"}`

#### `GET /api/usage` → `UsageStatus`

```json
{
  "gemini_status": "green",
  "groq_status": "green",
  "gemini_rpm_current": 0,
  "groq_rpm_current": 0
}
```

### WebSocket

`WS /ws/progress/{id}` → Redis pub/sub. Mesaj formatı:

```json
{ "stage": "mimar", "message": "Mimar ajanı modül bağımlılıklarını çözümlüyor...", "progress_pct": 50 }
```

---

## 7. Klasör Yapısı

```
repo-arkeolog/
├── frontend/                       # Next.js 14
│   ├── app/
│   │   ├── page.tsx                # Landing — URL input
│   │   ├── layout.tsx              # FOUC engelleyen inline theme init
│   │   ├── analysis/[id]/page.tsx  # Sonuç sayfası
│   │   └── api/chat-proxy/route.ts # Chat proxy (opsiyonel)
│   ├── components/
│   │   ├── tabs/{Summary,Mimap,Timeline,Chat}Tab.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── HealthBadge.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── ui/                     # primitive'ler
│   ├── lib/{api,socket}.ts
│   ├── public/                     # statik varlıklar
│   └── Dockerfile                  # Next.js standalone build
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + CORS
│   │   ├── api/
│   │   │   ├── analyze.py          # /analyze, /analysis/{id}
│   │   │   ├── chat.py             # /chat/{id} (SSE)
│   │   │   ├── ws.py               # /ws/progress/{id}
│   │   │   └── health.py           # /health, /usage
│   │   ├── models.py               # SQLAlchemy Mapped models
│   │   ├── schemas.py              # Pydantic v2
│   │   ├── db.py                   # session + engine
│   │   ├── config.py               # pydantic-settings
│   │   ├── tasks/
│   │   │   ├── celery_app.py
│   │   │   └── analyze_task.py     # Orkestratör
│   │   ├── pipeline/
│   │   │   ├── miner.py            # Smart clone + metadata
│   │   │   ├── chunker.py          # tree-sitter (11 dil, lazy cache)
│   │   │   └── embedder.py         # Gemini + Qdrant
│   │   ├── agents/
│   │   │   ├── base.py             # BaseAgent ABC + AgentContext
│   │   │   ├── plan_agent.py
│   │   │   ├── mimar_agent.py
│   │   │   ├── tarihci_agent.py
│   │   │   ├── dedektif_agent.py
│   │   │   └── onboarding_agent.py
│   │   ├── llm/
│   │   │   ├── cerebras.py         # 5 ajanın asıl istemcisi
│   │   │   ├── gemini.py           # embedding + chat streaming
│   │   │   ├── groq.py             # mevcut ama kullanılmıyor
│   │   │   └── usage_tracker.py
│   │   ├── rag/{retriever,chat_chain}.py
│   │   └── utils/{github,progress}.py
│   ├── alembic/versions/001_initial.py
│   ├── Dockerfile                  # python:3.11-slim
│   ├── start-web.sh
│   ├── start-worker.sh             # --pool=solo
│   ├── pyproject.toml
│   └── .env.example
│
├── infra/
│   ├── docker-compose.yml          # postgres + redis + qdrant (yerel dev)
│   └── Dockerfile.backend          # eski/yedek imaj
│
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/{feature,bug}.md + config.yml
│
├── ARCHITECTURE.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── AI_USAGE.md
├── DEPLOY_RAILWAY.md
├── developer.md                    # bu doküman
└── README.md
```

---

## 8. Ajan İmplementasyonları

Tüm ajanlar `BaseAgent` arayüzünü implemente eder:

```python
class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, ctx: AgentContext) -> dict: ...

    async def emit(self, ctx, message, pct):
        await push_progress(ctx.analysis_id, self.name, message, pct)
```

`AgentContext` alanları: `analysis_id`, `repo_path`, `repo_metadata`, `plan`, `previous_outputs`.

### 8.1. Plan Agent — `plan_agent.py`

- Girdi: `ctx.repo_metadata` (dil, framework, dosya/commit/contributor sayıları)
- LLM: Cerebras
- Çıktı: `{summary, agent_plan: {mimar, tarihci, dedektif}, estimated_complexity}`

### 8.2. Mimar Agent — `mimar_agent.py`

- Klasör ağacı (max derinlik 4, kara liste: `node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`)
- İmport grafı: Python `from ... import` + JS/TS `import / require('...')` regex'i (sadece relative)
- LLM çıktısı: `{architecture_pattern, modules: [{path, purpose, depends_on, dependents}], warnings, summary}`
- Frontend için Cytoscape JSON `analyze.py:_to_cytoscape` ile üretilir.

### 8.3. Tarihçi Agent — `tarihci_agent.py`

- 150 commit üst sınırı + akıllı seçim
- Hot files: ilk 500 commit'ten dosya değişim sayıları
- LLM çıktısı: `{story_summary, milestones, hot_files, contributor_summary, summary_note}`

### 8.4. Dedektif Agent — `dedektif_agent.py`

- Lint: ruff (Python) veya `npx eslint` (JS/TS)
- Vulture (Python, min-confidence 80)
- TODO/FIXME/HACK/XXX/NOTE: 20+ uzantı, 3 yorum stili (`#`, `//`, `/* */`)
- 9 paket yöneticisi: npm, pip, pyproject, Go mod, Cargo, Maven, Gradle, NuGet, Bundler, Composer
- LLM çıktısı: `{health_score, summary, issues, stats}`

### 8.5. Onboarding Agent — `onboarding_agent.py`

- Girdi: önceki 3 ajanın çıktısı + plan özeti
- LLM çıktısı: `{intro, day_1, day_2, day_3, first_pr_suggestion, people_to_ask, key_files_to_read, things_to_avoid}`

---

## 9. Frontend Notları

### 9.1. Sayfa Yapısı

- **`/`** — Landing: URL input + 3 demo butonu + tema toggle + alt 3 özellik kartı.
- **`/analysis/[id]`** — Sticky header (repo URL + HealthBadge + UsageStatusDot + ThemeToggle), ProgressBar (analiz bitene kadar), Tabs.

### 9.2. Mimap — Önemli Detaylar

- 8 rol: `entry / api / ui / business / data / util / config / test / other` (path heuristic).
- 4 layout: `concentric`, `dagre`, `cose`, `grid`.
- Klasör grupları: compound nodes (parent: klasör, children: dosyalar).
- Tarjan SCC ile döngü tespiti — iteratif (stack-safe).
- Cytoscape unmount race condition: cancellation token + try/catch teardown.
- PNG dışa aktarma.

### 9.3. Chat

Chat backend SSE'sini tüketir, mesaj-bazlı `sources / chunk / done` event'lerini render eder. Kaynak chunk'ları accordion'da gösterilir; `react-syntax-highlighter` ile kod render edilir.

### 9.4. Karanlık Tema

`app/layout.tsx` içinde inline script (head):

```js
(function(){try{
  var s=localStorage.getItem('theme');
  var p=window.matchMedia('(prefers-color-scheme: dark)').matches;
  if(s ? s==='dark' : p){document.documentElement.classList.add('dark');}
}catch(e){}})();
```

Bu sayede React mount'tan **önce** tema uygulanır — FOUC (flash of unstyled content) yaşanmaz.

### 9.5. UsageStatusDot

Analiz sayfasında her 30 sn'de bir `/api/usage` polling. `gemini_status` veya `groq_status` red/yellow olursa rozet rengi değişir.

---

## 10. GitHub Akışı

Detaylar: [`CONTRIBUTING.md`](CONTRIBUTING.md). Özet:

- `main` direkt push **yasak** — tüm değişiklikler PR.
- Branch: `feature/<ad>`, `fix/<ad>`, `docs/<ad>`, `refactor/<ad>`, `chore/<ad>`.
- Commit: Conventional Commits (`feat:`, `fix:`, `refactor:`, …) Türkçe veya İngilizce.
- PR şablonu (`.github/PULL_REQUEST_TEMPLATE.md`) — **AI Traceability bölümü zorunlu**.
- Squash merge tercih.
- Conflict: `git fetch && git rebase origin/main && git push --force-with-lease`.

---

## 11. Kurulum ve Çalıştırma

### Gereksinimler

- Node.js 20+
- Python 3.11–3.12
- Docker + Docker Compose *(yerel postgres/redis/qdrant için)*
- API keys: `CEREBRAS_API_KEY` (zorunlu), `GEMINI_API_KEY` *(opsiyonel — chat için)*

### Yerel Geliştirme

```bash
# 1) Altyapı
cd infra && docker compose up -d && cd ..

# 2) Backend
cd backend
cp .env.example .env                            # CEREBRAS_API_KEY ekle
python -m venv .venv && .venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# Terminal 1
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Windows için --pool=solo şart
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# 3) Frontend
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev    # http://localhost:3000
```

### .env Şablonları

`backend/.env.example`:
```
DATABASE_URL=postgresql://repoarkeolog:repoarkeolog@localhost:5432/repoarkeolog
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=
CEREBRAS_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
CORS_ORIGINS=*
ADMIN_WEBHOOK_URL=
```

`frontend/.env.local.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 12. Deploy

Tek Railway projesinde 5 servis: postgres, redis, backend, worker, frontend. Detaylı adım adım rehber: [`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md).

Canlı URL: https://frontend-production-9e092.up.railway.app/

---

## 13. Risk ve Sorun Giderme

| Belirti | Olası Sebep / Çözüm |
|---|---|
| Backend 502 (Railway) | Worker logu → `psycopg2`/`alembic` hatası. `DATABASE_URL` doğru mu? `start-web.sh` migrate başarısız mı? |
| WebSocket bağlanmıyor | Prod'da `wss://` kullan, `NEXT_PUBLIC_WS_URL` build time'da doğru olmalı. |
| CORS error | Frontend domain'ini backend'in `CORS_ORIGINS` env'ine ekle, backend redeploy. |
| Worker görev almıyor | Backend ve Worker aynı `REDIS_URL`'i mi kullanıyor? Worker log "celery@... ready" gösteriyor mu? |
| Windows'ta worker `PermissionError` | `--pool=solo` flag'i unutulmuş. |
| tree-sitter parser yüklenemez | Pip wheel uyumsuzluğu — Python 3.13'e geçersen 3.11/3.12'ye geri dön. |
| Cerebras 429/timeout | Retry layer 5 deneme yapar; ısrarla başarısız olursa `tarihci_output` benzeri alanlar `{"error": ...}` ile kalır, pipeline yine `done` bitirir. |
| Chat hiçbir şey döndürmüyor | `QDRANT_URL` veya `GEMINI_API_KEY` boş, ya da o repo için embedding adımı atlanmış. |
| Cytoscape 500+ düğümde donuyor | MimapTab klasör seviyesinde compound node grupları otomatik açıyor; rol filtresiyle azalt. |

### Demo Repoları (Landing'de hazır)

- `pallets/flask`
- `tiangolo/fastapi`
- `vercel/next.js`

---

**Son Güncelleme:** 2026-05-12 — hackathon teslimi sonrası dokümantasyon kod tabanıyla hizalandı.

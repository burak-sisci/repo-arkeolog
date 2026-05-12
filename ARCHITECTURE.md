# RepoArkeolog — Sistem Mimarisi

> Bu dosya **Plan Agent** çıktısı olarak üretilir ve süreç boyunca güncellenir (şartname §5.2).

---

## Genel Bakış

RepoArkeolog, bir GitHub reposunu **5 AI ajanı** ile analiz edip sonucu interaktif bir web arayüzünde sunan bir araçtır. Beş ajanın tamamı **Cerebras Inference** üzerinde, `qwen-3-235b-a22b-instruct-2507` modeliyle çalışır. Chat/RAG hattı ise **Gemini** üzerinden gider: `gemini-embedding-001` (768 boyut) + `gemini-2.5-flash` streaming.

---

## Katman Diyagramı

```
┌────────────────────┐  HTTP+WS  ┌──────────────────────────────┐
│ Next.js 14 (web)   │──────────▶│ FastAPI                       │
│ — landing          │           │  POST /api/analyze            │
│ — analiz sayfası   │◀──────────│  GET  /api/analysis/{id}      │
│ — Özet, Mimap,     │           │  POST /api/chat/{id}  (SSE)   │
│   Timeline, Chat   │           │  GET  /api/health, /api/usage │
│ — Karanlık tema    │           │  WS   /ws/progress/{id}       │
└────────────────────┘           └─────────────┬─────────────────┘
                                               │ Celery (Redis broker)
                                               ▼
                                  ┌───────────────────────────┐
                                  │ Worker — analyze_repo     │
                                  │  1) Mining (clone+chunk   │
                                  │     +embed opsiyonel)     │
                                  │  2) Plan Agent            │
                                  │  3) Mimar Agent           │
                                  │  4) Tarihçi Agent         │
                                  │  5) Dedektif Agent        │
                                  │  6) Onboarding Agent      │
                                  └───┬──────────┬────────────┘
                                      │          │
                       ┌──────────────┘          └─────────────┐
                       ▼                                       ▼
            ┌────────────────────┐                  ┌────────────────────┐
            │ PostgreSQL         │                  │ Cerebras API        │
            │ analyses,          │                  │ qwen-3-235b         │
            │ chat_messages      │                  │ (5 ajan)            │
            └────────────────────┘                  └────────────────────┘
                       ▲                                       ▲
                       │                                       │
                       │                            ┌──────────┴─────────┐
                       │                            │ Gemini API          │
                       │                            │ embedding + chat    │
                       │                            │ (RAG hattı, ops.)   │
                       │                            └────────────────────┘
                       │
              ┌────────┴────────┐
              │ Qdrant (ops.)   │  *QDRANT_URL boşsa atlanır*
              └─────────────────┘
```

---

## Katmanlar

### 1. Frontend *(Next.js 14, Railway/Vercel)*

- `frontend/app/page.tsx` — landing + URL girişi, 3 hazır demo butonu, tema toggle
- `frontend/app/analysis/[id]/page.tsx` — sonuç sayfası, sekmeler, progress, sağlık rozeti, usage dot
- `frontend/components/tabs/`
  - **SummaryTab** — özet, mimari pattern, sağlık skoru, onboarding kılavuzu
  - **MimapTab** — Cytoscape + cytoscape-dagre; rol sınıflandırması (8 rol), döngü tespiti, klasör grupları, 4 layout (`concentric` / `dagre` / `cose` / `grid`), in/out komşu listeleri, PNG dışa aktarma
  - **TimelineTab** — vis-timeline ile milestones, hot files, contributor özeti
  - **ChatTab** — SSE streaming chat (RAG aktifse)
- `frontend/components/ProgressBar.tsx` — WebSocket dinler, canlı progress yayar
- `frontend/components/HealthBadge.tsx` — sağlık skoru rozeti (yeşil/sarı/kırmızı)
- `frontend/components/ThemeToggle.tsx` — class-based dark mode + localStorage + FOUC engelleyen inline init (`layout.tsx` içinde)
- `frontend/lib/api.ts`, `frontend/lib/socket.ts` — REST ve WS istemcileri

### 2. Backend API *(FastAPI)*

| Endpoint | Görev |
|----------|-------|
| `POST /api/analyze` | Analizi başlatır, Celery'ye iletir, default branch'i GitHub API'den otomatik tespit eder. Cache hit varsa direkt döner. |
| `GET /api/analysis/{id}` | Durum + sonuç (status: `pending`/`running`/`done`/`failed`) |
| `POST /api/chat/{id}` | RAG (Server-Sent Events streaming) |
| `WS /ws/progress/{id}` | Redis pub/sub ile canlı durum yayını |
| `GET /api/health` | `{"status": "ok"}` |
| `GET /api/usage` | LLM RPM göstergeleri (`gemini_status`, `groq_status`, `gemini_rpm_current`, `groq_rpm_current`) |

CORS, `CORS_ORIGINS` env değişkeniyle yönetilir (virgülle ayrılmış origin listesi; `*` sadece geliştirme için).

### 3. Celery Worker

Worker `--pool=solo` ile başlar (Windows uyumluluğu). Pipeline sıralı:

| Aşama | İşlem | LLM | Çıktı |
|-------|-------|-----|-------|
| Mining | Smart git clone + tree-sitter chunk + (ops.) embedding | — | chunks, metadata |
| Plan | Repo metadata → ajan planı | Cerebras | `plan_output` |
| Mimar | İmport grafı + klasör ağacı | Cerebras | `mimar_output` |
| Tarihçi | Akıllı commit seçimi + hot files | Cerebras | `tarihci_output` |
| Dedektif | Lint + vulture + TODO + dep manifestleri | Cerebras | `dedektif_output` |
| Onboarding | Plan + 3 ajan sentezi | Cerebras | `onboarding_output` |

Her aşama Redis `progress:{analysis_id}` kanalına ilerleme yayar.

### 4. Veri Katmanı

| Depo | Görev |
|------|-------|
| PostgreSQL | `analyses`, `chat_messages` tabloları. Cache anahtarı `repo_hash = sha256(repo_url:branch)` (hexdigest, 64 char). |
| Redis | Celery broker + result backend + WebSocket pub/sub |
| Qdrant | Kod chunk vektörleri (koleksiyon adı `repo_{analysis_id}`, 768 boyut, COSINE) — *yalnız `QDRANT_URL` + `GEMINI_API_KEY` doluysa* |

### 5. Pipeline Detayları

#### 5.1. Smart Clone *(`backend/app/pipeline/miner.py`)*

- `--depth 50` (Tarihçi için yeterli, history şişmez)
- `--filter=blob:limit=1m` (büyük binary/LFS lazy)
- `--single-branch`
- 4 kademeli fallback: (hedef branch + filter) → (hedef branch, filter yok) → (HEAD + filter) → (HEAD, filter yok)

#### 5.2. Çoklu Dil Chunklayıcı *(`backend/app/pipeline/chunker.py`)*

11 dil + tree-sitter parser kayıtları **lazy-loaded** (`_PARSER_CACHE`). Sınıf içi metodlar dahil edilir. Parser yüklenemezse veya tree boşsa tüm dosya tek `module` chunk olur. Dosya boyutu üst sınırı 200 KB, chunk gövde sınırı 4000 char.

| Dil | Uzantılar |
|-----|-----------|
| Python | `.py` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` |
| TypeScript | `.ts`, `.tsx` |
| Java | `.java` |
| Go | `.go` |
| Rust | `.rs` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh` |
| C# | `.cs` |
| Ruby | `.rb` |
| PHP | `.php` (tree-sitter `language_php_only()`) |

#### 5.3. Mimari Graf Üretimi *(`backend/app/agents/mimar_agent.py`)*

Klasör ağacı + Python/JS/TS import regex'i ile ön bağımlılık çıkarımı; sonuç Cerebras LLM'e gönderilir, modüller rol/açıklama ile zenginleştirilir. Frontend'e dönen Cytoscape JSON `analyze.py:_to_cytoscape` içinde üretilir.

#### 5.4. Sağlık Raporu *(`backend/app/agents/dedektif_agent.py`)*

- Lint: `ruff` (Python) veya `npx eslint` (JS/TS)
- Ölü kod: `vulture` (Python, `--min-confidence 80`)
- TODO/FIXME/HACK/XXX/NOTE regex'i — 20+ dosya uzantısı (Python, JS/TS, Java, Kotlin, Scala, Go, Rust, C ailesi, C#, Ruby, PHP, Swift)
- Bağımlılık manifestleri: `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `*.csproj`, `Gemfile`, `composer.json`

#### 5.5. Akıllı Commit Seçimi *(`backend/app/agents/tarihci_agent.py`)*

150 commit üst sınırı. >150 commit'te seçim: ilk 10, son 30, tüm merge'ler, top-%20 büyük diff, aylık örnekleme. Sonuç `summary_note` ile kullanıcıya raporlanır ("Bu repo X commit içeriyor — Tarihçi temsili 150 commit üzerinden hikaye çıkardı.").

#### 5.6. RAG Hattı *(`backend/app/rag/`)*

- `retriever.py` — Gemini ile sorgu embed → Qdrant `search` (top 8) → dosya yolu anahtar kelime boost'u → top 5 döner
- `chat_chain.py` — kod chunk'ları + mimar/dedektif çıktısından soruyla ilgili alt küme → Gemini `gemini-2.5-flash` streaming → SSE event akışı (`sources`, `chunk`, `done`)

---

## Tasarım Kararları *(ADR özetleri)*

- **Asenkron işlem:** Repo analizi 1–5 dk. Celery + WebSocket ile non-blocking.
- **Fail-soft:** Bir ajan çökse pipeline durmaz; hata `failed` etiketiyle saklanır (`mimar_output = {"error": "...", "status": "failed"}`). Onboarding ajanı çökse de analiz `done` sayılır.
- **Cache-first:** `repo_hash = sha256(url:branch)` ile aynı repo + branch tekrar analiz edilmez.
- **Token tasarrufu:** Ajanlara meta + chunk özeti + plan alt görevleri gönderilir, ham kod değil. Çok büyük repolarda chunk sayısı 5000'e sınırlandırılır (sınıf > fonksiyon > modül önceliği, kök yakını önce).
- **Dayanıklı LLM çağrısı:** 240 sn timeout + 5 kademeli (Cerebras) / 8 kademeli (Gemini) üstel backoff. Gemini'de 5 RPM koruması için 13 sn istek-arası throttle (`MIN_INTERVAL`).
- **Çoklu dil çatısı:** Tek `LANG_EXTENSIONS` map + lazy parser cache. Yeni dil ≈ 5 satır.
- **Default branch:** GitHub API `default_branch` alanından çekilir. Kullanıcı `main` gönderirse repo'nun gerçek default'una geçilir.
- **Karanlık tema:** Tailwind `darkMode: "class"` + localStorage + `app/layout.tsx` içinde inline script ile FOUC engellenir.

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Web | Next.js 14.2, TypeScript 5, TailwindCSS 3, @radix-ui (dialog, tabs) |
| Görselleştirme | Cytoscape.js + cytoscape-dagre + dagre, vis-timeline, react-syntax-highlighter |
| Chat istemcisi | Vercel AI SDK (`ai` v3) |
| Backend | FastAPI ≥0.111, Pydantic v2, Celery 5, uvicorn |
| ORM / Migration | SQLAlchemy 2.x + Alembic |
| DB | PostgreSQL 16, Redis 7 |
| Vektör | Qdrant *(opsiyonel)* |
| LLM (ajanlar) | Cerebras `qwen-3-235b-a22b-instruct-2507` |
| LLM (chat / embed) | Gemini `gemini-2.5-flash` + `gemini-embedding-001` *(opsiyonel)* |
| Statik analiz | ruff, eslint, vulture, radon |
| Parser | tree-sitter (11 dil) |
| Çalışma zamanı | Python 3.11–3.12, Node.js 20 |

> Not: `backend/app/llm/groq.py` istemcisi kod tabanında mevcuttur (Llama 3.3 70B) ancak şu an hiçbir ajan tarafından kullanılmaz; yedek/fallback rolü için saklanır.

---

## Güncelleme Geçmişi

- 2026-05-05 — İlk plan (Plan Agent çıktısı).
- 2026-05-06 — 11 dil desteği, Cerebras geçişi, smart clone, dark theme.
- 2026-05-07 — Mimari Harita zenginleştirmesi, default branch otomatik tespiti, repo limiti 2 GB.
- 2026-05-08+ — Railway deploy (Dockerfile'lar, env-driven config, Next.js 14.2.35'e yükseltme, cytoscape-dagre tip tanımı).
- 2026-05-12 — Md dosyaları kod tabanıyla hizalandı (post-hackathon).

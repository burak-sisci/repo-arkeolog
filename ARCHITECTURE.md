# RepoArkeolog — Sistem Mimarisi

> Bu dosya **Plan Agent** çıktısı olarak üretilir ve süreç boyunca güncellenir (şartname §5.2).

---

## Genel Bakış

RepoArkeolog, bir GitHub reposunu **5 AI ajanı** ile analiz edip sonucu interaktif bir web arayüzünde sunan bir araçtır. Tüm LLM çağrıları **Cerebras Inference** üzerinde, `qwen-3-235b-a22b-instruct-2507` modeliyle gerçekleşir.

---

## Katman Diyagramı

```
┌────────────────────┐  HTTP+WS  ┌─────────────────────────────┐
│ Next.js 14 (web)   │──────────▶│ FastAPI                      │
│ — landing          │           │  /api/analyze                │
│ — analiz sayfası   │◀──────────│  /api/analysis/{id}          │
│ — Mimap, Timeline  │           │  /api/chat/{id}              │
│ — Chat, Tema       │           │  /ws/progress/{id}           │
└────────────────────┘           └────────────┬────────────────┘
                                              │ Celery (Redis broker)
                                              ▼
                                  ┌──────────────────────────┐
                                  │ Worker — analyze_repo    │
                                  │  1) mining (clone+chunk) │
                                  │  2) Plan Agent           │
                                  │  3) Mimar Agent          │
                                  │  4) Tarihçi Agent        │
                                  │  5) Dedektif Agent       │
                                  │  6) Onboarding Agent     │
                                  └─────┬──────────┬─────────┘
                                        │          │
                          ┌─────────────┘          └─────────────┐
                          ▼                                      ▼
                  ┌───────────────┐                    ┌───────────────┐
                  │ PostgreSQL    │                    │ Cerebras API   │
                  │ (cache, json) │                    │ qwen-3-235b    │
                  └───────────────┘                    └───────────────┘
                          ▲
                          │
                  ┌───────┴───────┐
                  │ Qdrant (opt.) │  *chat/RAG için, şu an kapalı*
                  └───────────────┘
```

---

## Katmanlar

### 1. Frontend *(Next.js 14, Vercel/Railway)*
- `app/page.tsx` — landing + URL girişi
- `app/analysis/[id]/page.tsx` — sonuç sayfası
- `components/tabs/`
  - **SummaryTab** — özet, mimari pattern, sağlık skoru, onboarding
  - **MimapTab** — Cytoscape + dagre; rol sınıflandırması, döngü tespiti, klasör grupları, 4 layout
  - **TimelineTab** — vis-timeline milestones, hot files, contributor özet
  - **ChatTab** — RAG sohbet *(şu an kapalı)*
- `components/ProgressBar.tsx` — WebSocket ile canlı ilerleme
- `components/ThemeToggle.tsx` — class-based dark mode + localStorage + FOUC engelleyen inline init

### 2. Backend API *(FastAPI)*
- `POST /api/analyze` — analiz başlatır, Celery'ye iletir, default branch'i GitHub API'den otomatik tespit eder
- `GET /api/analysis/{id}` — durum + sonuç
- `POST /api/chat/{id}` — RAG (SSE)
- `WS /ws/progress/{id}` — canlı durum
- `GET /api/health` — health check
- `GET /api/usage` — LLM kullanım durumu

### 3. Celery Worker
Sıralı pipeline:

| Aşama | İşlem | LLM | Çıktı |
|-------|-------|-----|-------|
| Mining | Smart git clone + tree-sitter chunk + (opsiyonel) embedding | — | chunks, metadata |
| Plan | Repo metadata → ajan planı | Cerebras | `plan_output` |
| Mimar | İmport grafiği + klasör ağacı | Cerebras | `mimar_output` |
| Tarihçi | Commit istatistikleri + hot files | Cerebras | `tarihci_output` |
| Dedektif | Lint + TODO + dep manifestleri | Cerebras | `dedektif_output` |
| Onboarding | 3 ajan sentezi | Cerebras | `onboarding_output` |

### 4. Veri Katmanı

| Depo | Görev |
|------|-------|
| PostgreSQL | Analiz sonuçları (`analyses`), chat (`chat_messages`), cache anahtarı = `repo_hash` |
| Redis | Celery broker + WebSocket pub/sub |
| Qdrant | Kod chunk vektörleri (her repo bir koleksiyon) — *chat aktifse* |

### 5. Pipeline Detayları

#### 5.1. Smart Clone *(`pipeline/miner.py`)*
- `--depth 50` (Tarihçi için yeterli)
- `--filter=blob:limit=1m` (büyük binary/LFS lazy)
- 4 kademeli fallback: (hedef branch + filter) → (filter yok) → (HEAD + filter) → (HEAD)

#### 5.2. Çoklu Dil Chunklayıcı *(`pipeline/chunker.py`)*
11 dil + tree-sitter parser kayıtları lazy-loaded. Sınıf içi metodlar dahil edilir. Boş tree → tüm dosya tek modül chunk.

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
| PHP | `.php` |

#### 5.3. Mimari Graf Üretimi *(`agents/mimar_agent.py`)*
Klasör ağacı + python/js import regex'i ile ön bağımlılık çıkarımı; Cerebras LLM modülerleştirir, rol/açıklama ekler.

#### 5.4. Sağlık Raporu *(`agents/dedektif_agent.py`)*
Lint *(ruff/eslint)*, TODO/FIXME/HACK regex'i (11 dil), bağımlılık manifesti tarama (`package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `Gemfile`, `composer.json`).

---

## Tasarım Kararları *(ADR özetleri)*

- **Asenkron işlem:** Repo analizi 1–5 dk. Celery + WebSocket ile non-blocking.
- **Fail-soft:** Bir ajan çökse pipeline durmaz; hata `failed` etiketiyle saklanır.
- **Cache-first:** `repo_hash = sha256(url:branch)` ile aynı repo + branch tekrar analiz edilmez.
- **Token tasarrufu:** Ajanlara meta + chunk özeti gönderilir, ham kod değil.
- **Dayanıklı LLM çağrısı:** 240 sn timeout + 8 kademeli üstel backoff (429/503/timeout/overloaded).
- **Çoklu dil çatısı:** Tek `LANG_EXTENSIONS` map + lazy parser cache. Yeni dil ≈ 5 satır.
- **Default branch:** GitHub API'den çekilir. `main` zorunluluğu yok.

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Web | Next.js 14, TypeScript, TailwindCSS |
| Görselleştirme | Cytoscape.js + cytoscape-dagre, vis-timeline |
| Backend | FastAPI, Pydantic v2, Celery 5 |
| ORM | SQLAlchemy 2.x + Alembic |
| DB | PostgreSQL 17, Redis 7 |
| Vektör | Qdrant *(opsiyonel)* |
| LLM | Cerebras `qwen-3-235b-a22b-instruct-2507` |
| Statik analiz | ruff, eslint, vulture, radon |
| Parser | tree-sitter (11 dil) |

---

## Güncelleme Geçmişi
- 2026-05-05 — İlk plan (Plan Agent çıktısı).
- 2026-05-06 — 11 dil desteği, Cerebras geçişi, smart clone, dark theme.
- 2026-05-07 — Mimari Harita zenginleştirmesi, default branch otomatik tespiti, repo limiti 2 GB.

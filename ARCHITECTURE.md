# RepoArkeolog — Sistem Mimarisi

## Genel Bakış

RepoArkeolog, bir GitHub reposunu çoklu AI ajanıyla analiz eden, sonuçları interaktif bir web arayüzünde sunan bir araçtır.

## Katmanlar

### 1. Frontend (Next.js 14 — Vercel)
- `app/page.tsx` — GitHub URL giriş ekranı
- `app/analysis/[id]/page.tsx` — Analiz sonuç sayfası (Özet, Mimap, Timeline, Chat sekmeleri)
- `components/ProgressBar.tsx` — WebSocket ile canlı ajan ilerleme takibi
- `components/tabs/MimapTab.tsx` — Cytoscape.js bağımlılık grafiği
- `components/tabs/TimelineTab.tsx` — vis-timeline commit tarihi
- `components/tabs/ChatTab.tsx` — RAG tabanlı sohbet arayüzü

### 2. Backend API (FastAPI — Railway)
- `POST /api/analyze` — Analiz başlatır, Celery task kuyruğa ekler
- `GET /api/analysis/{id}` — Durum ve sonuç döner
- `POST /api/chat/{id}` — RAG tabanlı sohbet (Server-Sent Events)
- `WS /ws/progress/{id}` — Canlı ajan durumu WebSocket

### 3. Celery Worker
Asenkron analiz pipeline'ı:
1. **Mining** — git clone + tree-sitter AST parse + Gemini embedding + Qdrant yazım
2. **Plan Agent** — Repo metadata → ajan planı (Gemini)
3. **Mimar Ajan** — İmport grafiği + klasör yapısı → mimari harita (Gemini)
4. **Tarihçi Ajan** — Git log → evrim hikayesi (Groq Llama)
5. **Dedektif Ajan** — ruff/eslint + vulture + TODO grep → sağlık raporu (Gemini)
6. **Onboarding Ajan** — 3 ajan sentezi → ilk hafta yol haritası (Gemini)

### 4. Veri Katmanı
| Depo | Görev |
|---|---|
| PostgreSQL | Analiz sonuçları, chat mesajları |
| Redis | Celery broker + pub/sub (WebSocket events) |
| Qdrant | Kod chunk vektörleri (her repo = ayrı koleksiyon) |

### 5. Dış Servisler
| Servis | Görev |
|---|---|
| Gemini 2.5 Flash | Plan, Mimar, Dedektif, Onboarding ajanları |
| Gemini text-embedding-004 | Kod chunk ve query embedding |
| Groq Llama 3.3 70B | Tarihçi ajan (hızlı, ücretsiz) |
| GitHub API | Repo doğrulama + metadata |

## Tasarım Kararları

- **Asenkron işlem:** Repo analizi 1-5 dk sürebilir; Celery+WebSocket ile non-blocking.
- **Fail-soft:** Bir ajan çökerse diğerleri devam eder.
- **Cache-first:** Aynı repo tekrar analiz edilmez (repo_hash ile).
- **Token tasarrufu:** Ajanlara sadece metadata gönderilir, ham kod değil.
- **Rate limit koruması:** Gemini 15 RPM → ajanlar sıralı çalışır; Groq fallback.

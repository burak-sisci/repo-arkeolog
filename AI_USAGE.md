# AI Kullanım Kayıtları — RepoArkeolog (SolveX 2026)

Bu doküman, projenin geliştirilmesi sürecinde kullanılan AI ajanlarının (Plan Agent + Skills Agent) etkileşim çıktılarını ve hangi modüllerin AI yardımıyla üretildiğini şartname §5 ve §6 uyarınca kaydeder.

---

## 1. Kullanılan AI Ekosistemi

| Bileşen | Servis | Amaç |
|---------|--------|------|
| Plan Agent | Claude (Anthropic) + Cerebras Inference | Mimari plan, alt görev üretimi |
| Skills Agent | Cerebras `qwen-3-235b-a22b-instruct-2507` | Uzman görev (algoritma, refactor, optimizasyon) |
| Geliştirme ortamı | Claude Code (Anthropic) | AI-Native IDE benzeri akış |
| Çalışma zamanı LLM (5 ajan) | Cerebras `qwen-3-235b-a22b-instruct-2507` | Plan, Mimar, Tarihçi, Dedektif, Onboarding ajan inferansları |
| Çalışma zamanı LLM (chat/RAG) | Gemini `gemini-2.5-flash` + `gemini-embedding-001` *(opsiyonel)* | Chat streaming + kod embedding (768 boyut) |

---

## 2. Plan Agent Etkileşimleri

### 2.1. Mimari Plan

- **Tarih:** 2026-05-05
- **Çıktı:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Prompt özeti:** "RepoArkeolog projesi için 5 ajanlı pipeline mimarisi tasarla. FastAPI + Celery + Postgres + Redis + Qdrant katmanlarını çıkar; veri akışını ve servis sorumluluklarını tanımla."
- **Çıktının kullanımı:** `backend/app/agents/`, `backend/app/pipeline/`, `backend/app/api/` modüllerinin iskeletini bu plan belirledi.

### 2.2. Yol Haritası

- **Tarih:** 2026-05-05
- **Çıktı:** [`ROADMAP.md`](ROADMAP.md)
- **Prompt özeti:** "MVP kapsamını ve stretch goal'leri belirle. Her görevi alt-görevlere böl ve sahibini ata."

### 2.3. Sub-task Üretimi

Plan Agent'ın belirlediği alt görevler GitHub Issue'larına dönüştürüldü. Her Issue, ilgili geliştiriciye atandı (şartname §6).

---

## 3. Skills Agent Etkileşimleri

### 3.1. Çoklu Dil Tree-sitter Yöneticisi

- **Modül:** `backend/app/pipeline/chunker.py`
- **Tarih:** 2026-05-06
- **Görev:** 11 dil için tree-sitter parser kayıtlarını lazy-load eden, dile özgü function/class düğümlerini tanıyan birleşik chunklayıcı. PHP için `language_php_only()` özel durumu dahil.
- **AI rolü:** Algoritma uzmanı — node tip kümeleri, sınıf-içi metod yakalama, parser yüklenememe/parse hatası fallback davranışları.

### 3.2. Tarjan SCC ile Döngü Tespiti

- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-06
- **Görev:** Bağımlılık grafiğindeki döngüleri (circular dependencies) iteratif Tarjan algoritmasıyla tespit etmek; büyük graflarda stack overflow'dan kaçınmak.
- **AI rolü:** Algoritma uzmanı.

### 3.3. LLM Retry & Throttle Katmanı

- **Modüller:** `backend/app/llm/cerebras.py`, `backend/app/llm/gemini.py`
- **Tarih:** 2026-05-06
- **Görev:** 429/500/502/503/504/timeout/overloaded hatalarında üstel backoff; Cerebras için 240 sn timeout + 5 kademeli retry; Gemini için 8 kademeli retry + `retry_delay` parser + 13 sn'lik istek arası throttle (5 RPM koruması).
- **AI rolü:** Distributed-systems uzmanı.

### 3.4. Smart Clone Stratejisi

- **Modül:** `backend/app/pipeline/miner.py`
- **Tarih:** 2026-05-06
- **Görev:** `--depth 50` + `--filter=blob:limit=1m` + `--single-branch` ile büyük binary/LFS atlanması; 4 kademeli klon fallback (hedef branch + filter → hedef branch, filter yok → HEAD + filter → HEAD).
- **AI rolü:** Git internals uzmanı.

### 3.5. Default Branch Otomatik Tespiti

- **Modüller:** `backend/app/api/analyze.py`, `backend/app/utils/github.py`
- **Tarih:** 2026-05-07
- **Görev:** GitHub API'den dönen `default_branch` ile `main`/`master`/`develop` farkını şeffaf şekilde ele almak; private/404 ayrımı yapmak.
- **AI rolü:** API entegrasyon uzmanı.

### 3.6. Cytoscape Unmount Race Condition

- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-06
- **Görev:** React StrictMode + cytoscape async layout sırasında destroy'da yaşanan null-deref hatası için cancellation token + try/catch teardown.
- **AI rolü:** React internals uzmanı.

### 3.7. Karanlık Tema Class-Based + FOUC Engelleme

- **Modüller:** `frontend/app/layout.tsx`, `frontend/app/globals.css`, `frontend/components/ThemeToggle.tsx`
- **Tarih:** 2026-05-06
- **Görev:** Tailwind `darkMode: "class"` + localStorage persistence + render öncesi inline script ile flash-of-unstyled-content engelleme. Tema React mount'tan önce uygulanır.
- **AI rolü:** Frontend performans uzmanı.

### 3.8. Mimari Harita Zenginleştirmesi

- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-07
- **Görev:** Rol sınıflandırması (8 rol, path heuristic), 4 layout (`concentric`/`dagre`/`cose`/`grid`), klasör grupları (compound nodes), rol filtresi, döngü tespiti, in/out neighbor listeleri, PNG dışa aktarma.
- **AI rolü:** Veri görselleştirme uzmanı.

### 3.9. Akıllı Commit Seçimi

- **Modül:** `backend/app/agents/tarihci_agent.py`
- **Tarih:** 2026-05-07
- **Görev:** Büyük repolarda 150 commit üst sınırını koruyarak temsili örnekleme: ilk 10, son 30, tüm merge'ler, top-%20 büyük diff, aylık örnekleme. Sonuç `summary_note` ile kullanıcıya iletilir.
- **AI rolü:** Algoritma uzmanı.

### 3.10. Çok Dilli Bağımlılık Manifest Taraması

- **Modül:** `backend/app/agents/dedektif_agent.py` (`_check_deps`)
- **Tarih:** 2026-05-07
- **Görev:** 9 paket yöneticisi için tek noktadan manifest taraması (npm, pip, pyproject, Go modules, Cargo, Maven, Gradle, NuGet, Bundler, Composer).
- **AI rolü:** Build/paket yöneticisi uzmanı.

---

## 4. Refactoring & Optimization Passes

| Tarih | Kapsam | Not |
|-------|--------|-----|
| 2026-05-06 | LLM client retry layer | Gemini → Groq → Cerebras geçişinde ortak abstraction |
| 2026-05-07 | MimapTab tek dosya rewrite | 161 → 408 satır, eski ile davranış uyumlu |
| 2026-05-07 | Frontend dark mode tüm tab'lara | 8 dosyada `dark:` variantları |
| 2026-05-08 | Railway deploy hazırlığı | `backend/Dockerfile`, `frontend/Dockerfile` (standalone build), `start-web.sh`, `start-worker.sh`, env-driven CORS |
| 2026-05-09 | Next.js 14.2.35'e yükseltme | CVE-2025-55184, CVE-2025-67779 |
| 2026-05-10 | tsconfig target `es2017` | Set iteration build hatası |
| 2026-05-11 | cytoscape-dagre tip tanımı | TypeScript modül bildirimi eklendi |
| 2026-05-12 | Md dosyaları kod tabanıyla hizalandı | Final dokümantasyon pass'i |

---

## 5. AI Traceability Etiketleme Politikası

Tüm yeni veya yeniden yazılmış kritik fonksiyonlar şu yorumla işaretlenir:

```python
# AI: <Plan|Skills> Agent (<model>) — <kısa açıklama>
```

Bu etiket, dosya başında veya fonksiyonun hemen üstünde yer alır. PR açıklamasında "AI Traceability" bölümü bu etiketlerin özetini içerir.

---

## 6. Notlar

- Çalışma zamanında **5 ajanın tümü** `app.llm.cerebras.cerebras_client` üzerinden çalışır. Bazı ajan modüllerinde alias `import` ifadeleri tarihsel olarak `gemini_client`/`groq_client` adlarını korusa da gerçek istemci Cerebras'tır.
- `backend/app/llm/groq.py` (Llama 3.3 70B) ve `backend/app/llm/gemini.py` istemcileri tabanda mevcuttur. Groq şu an ajanlar tarafından kullanılmaz (yedek). Gemini yalnızca **chat/RAG** hattında (embedding + streaming) devrededir.

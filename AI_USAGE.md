# AI Kullanım Kayıtları — RepoArkeolog (SolveX 2026)

Bu doküman, projenin geliştirilmesi sürecinde kullanılan AI ajanlarının (Plan Agent + Skills Agent) etkileşim çıktılarını ve hangi modüllerin AI yardımıyla üretildiğini şartname §5 ve §6 uyarınca kaydeder.

---

## 1. Kullanılan AI Ekosistemi

| Bileşen | Servis | Amaç |
|---------|--------|------|
| Plan Agent | Claude (Anthropic) + Cerebras Inference | Mimari plan, alt görev üretimi |
| Skills Agent | Cerebras `qwen-3-235b-a22b-instruct-2507` | Uzman görev (algoritma, refactor, optimizasyon) |
| Geliştirme ortamı | Claude Code (Anthropic) | AI-Native IDE benzeri akış |
| Çalışma zamanı LLM | Cerebras `qwen-3-235b-a22b-instruct-2507` | 5 ajanın inferans işlemleri |

---

## 2. Plan Agent Etkileşimleri

### 2.1. Mimari Plan
- **Tarih:** 2026-05-05
- **Çıktı:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Promt özeti:** "RepoArkeolog projesi için 5 ajanlı pipeline mimarisi tasarla. FastAPI + Celery + Postgres + Redis + Qdrant katmanlarını çıkar; veri akışını ve servis sorumluluklarını tanımla."
- **Çıktının kullanımı:** `backend/app/agents/`, `backend/app/pipeline/`, `backend/app/api/` modüllerinin iskeletini bu plan belirledi.

### 2.2. Yol Haritası
- **Tarih:** 2026-05-05
- **Çıktı:** [`ROADMAP.md`](ROADMAP.md)
- **Promt özeti:** "MVP kapsamını ve stretch goal'leri belirle. Her görevi alt-görevlere böl ve sahibini ata."

### 2.3. Sub-task Üretimi
Plan Agent'ın belirlediği alt görevler GitHub Issue'larına dönüştürüldü. Her Issue, ilgili geliştiriciye atandı (şartname §6).

---

## 3. Skills Agent Etkileşimleri

### 3.1. Çoklu Dil Tree-sitter Yöneticisi
- **Modül:** `backend/app/pipeline/chunker.py`
- **Tarih:** 2026-05-06
- **Görev:** 11 dil için tree-sitter parser kayıtlarını lazy-load eden, dile özgü function/class düğümlerini tanıyan birleşik chunklayıcı.
- **AI rolü:** Algoritma uzmanı — node tip kümeleri, sınıf-içi metod yakalama, fallback davranışları.

### 3.2. Tarjan SCC ile Döngü Tespiti
- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-06
- **Görev:** Bağımlılık grafiğindeki döngüleri (circular dependencies) iteratif Tarjan algoritmasıyla tespit etmek; büyük graflarda stack overflow'dan kaçınmak.
- **AI rolü:** Algoritma uzmanı.

### 3.3. Cerebras Retry & Throttle Katmanı
- **Modül:** `backend/app/llm/cerebras.py`, `backend/app/llm/gemini.py`
- **Tarih:** 2026-05-06
- **Görev:** 429/503/timeout/overloaded hatalarında üstel backoff + `retry_delay` parser; Gemini için 13 sn'lik istek arası throttle (5 RPM koruması).
- **AI rolü:** Distributed-systems uzmanı.

### 3.4. Smart Clone Stratejisi
- **Modül:** `backend/app/pipeline/miner.py`
- **Tarih:** 2026-05-06
- **Görev:** `--depth 50` + `--filter=blob:limit=1m` ile büyük binary/LFS atlanması, 4 kademeli klon fallback (hedef branch + filtre → filtre yok → HEAD + filtre → HEAD).
- **AI rolü:** Git internals uzmanı.

### 3.5. Default Branch Otomatik Tespiti
- **Modül:** `backend/app/api/analyze.py`, `backend/app/utils/github.py`
- **Tarih:** 2026-05-07
- **Görev:** GitHub API'den dönen `default_branch` ile `main`/`master`/`develop` farkını şeffaf şekilde ele almak.
- **AI rolü:** API entegrasyon uzmanı.

### 3.6. Cytoscape Unmount Race Condition
- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-06
- **Görev:** React StrictMode + cytoscape async layout sırasında destroy'da yaşanan null-deref hatası için cancellation token + try/catch teardown.
- **AI rolü:** React internals uzmanı.

### 3.7. Karanlık Tema Class-Based + FOUC Engelleme
- **Modüller:** `frontend/app/layout.tsx`, `frontend/app/globals.css`, `frontend/components/ThemeToggle.tsx`
- **Tarih:** 2026-05-06
- **Görev:** Tailwind `darkMode: "class"` + localStorage persistence + render öncesi inline script ile flash-of-unstyled-content engelleme.
- **AI rolü:** Frontend performans uzmanı.

### 3.8. Mimari Harita Zenginleştirmesi
- **Modül:** `frontend/components/tabs/MimapTab.tsx`
- **Tarih:** 2026-05-07
- **Görev:** Rol sınıflandırması (path heuristic), 4 layout (concentric/dagre/cose/grid), klasör grupları (compound nodes), rol filtresi, döngü tespiti, in/out neighbor listeleri, PNG dışa aktarma.
- **AI rolü:** Veri görselleştirme uzmanı.

---

## 4. Refactoring & Optimization Passes

| Tarih | Kapsam | Not |
|-------|--------|-----|
| 2026-05-06 | LLM client retry layer | Gemini → Groq → Cerebras geçişinde ortak abstraction |
| 2026-05-07 | MimapTab tek dosya rewrite | 161 → 408 satır, eski ile davranış uyumlu |
| 2026-05-07 | Frontend dark mode tüm tab'lara | 8 dosyada `dark:` variantları |

Final Review (proje tesliminden önce) ayrıca yapılacak ve burada raporlanacaktır.

---

## 5. AI Traceability Etiketleme Politikası

Tüm yeni veya yeniden yazılmış kritik fonksiyonlar şu yorumla işaretlenir:

```python
# AI: <Plan|Skills> Agent (<model>) — <kısa açıklama>
```

Bu etiket, dosya başında veya fonksiyonun hemen üstünde yer alır. PR açıklamasında "AI Traceability" bölümü bu etiketlerin özetini içerir.

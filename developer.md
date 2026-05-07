# RepoArkeolog — Geliştirici Dokümanı

> **Proje:** SolveX AI Hackathon 2026 — RepoArkeolog
> **Hedef:** Bir GitHub reposunu çoklu AI ajanıyla "kazıyıp" yeni gelen geliştiriciye 5 dakikada anlatan bir araç.
> **Demo formatı:** Sahne + projeksiyon, 3-5 dakika
> **Desteklenen diller:** Python, JavaScript, TypeScript (hard scope)
> **Bütçe:** Öncelik ücretsiz tier servisleri; gerekirse küçük ödemeli upgrade kabul

---

## İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Sistem Mimarisi](#2-sistem-mimarisi)
3. [İş Akış Şeması](#3-i̇ş-akış-şeması)
4. [Teknoloji Yığını ve Gerekçeler](#4-teknoloji-yığını-ve-gerekçeler)
5. [Veri Modelleri](#5-veri-modelleri)
6. [API Sözleşmesi](#6-api-sözleşmesi)
7. [Modül Modül Geliştirme Rehberi](#7-modül-modül-geliştirme-rehberi)
8. [AI Ajan Tasarımı ve Prompt'lar](#8-ai-ajan-tasarımı-ve-promptlar)
9. [Frontend Geliştirme Rehberi](#9-frontend-geliştirme-rehberi)
10. [GitHub Akışı ve Şartname Uyumluluğu](#10-github-akışı-ve-şartname-uyumluluğu)
11. [Test Stratejisi](#11-test-stratejisi)
12. [Demo Hazırlığı ve Risk Yönetimi](#12-demo-hazırlığı-ve-risk-yönetimi)
13. [Maliyet ve Kaynak Yönetimi](#13-maliyet-ve-kaynak-yönetimi)
14. [Kurulum ve Çalıştırma](#14-kurulum-ve-çalıştırma)

---

## 1. Proje Özeti

### 1.1. Ne Yapıyoruz?

RepoArkeolog, kullanıcıdan bir **GitHub repository URL'si** alır ve birden fazla AI ajanını paralel/sıralı şekilde çalıştırarak repoyu **dakikalar içinde analiz eder**. Çıktı, tek sayfalı interaktif bir webdir; içinde:

- **Özet rapor** (proje ne, ne işe yarar, sağlık durumu)
- **Gezinilebilir mimari haritası** (tıklanabilir bağımlılık grafiği)
- **Zaman çizelgesi** (projenin commit tabanlı evrimi)
- **Repoyla sohbet** (RAG tabanlı soru-cevap)

### 1.2. Neden Yapıyoruz?

**Problem:** Yeni bir geliştirici bir projeye katıldığında repoya alışması ortalama **1-2 hafta** sürer. Bu süreçte:
- Klasör yapısını anlamaya çalışır
- Hangi modülün ne işe yaradığını öğrenir
- Geçmişteki kararları (neden monolit, neden bu framework) keşfetmeye uğraşır
- Teknik borçları geç fark eder

**Çözümümüz:** AI ajanları bu keşif sürecini geliştirici yerine yapar, sonucu **5 dakikada** sunar.

### 1.3. Hackathon Şartnamesine Uyum

Şartname iki şey istiyor:
1. **Plan Agent** — projenin mimari planını çıkaran üst akıl
2. **Skills Agent** — uzmanlık alanlarında çalışan ajanlar (algoritma, güvenlik, vb.)

Bizim mimarimiz tam bu yapıyı **ürünün kendisi** olarak somutlaştırıyor. Bu meta-uyum jüri puanlamasında avantaj sağlar.

### 1.4. MVP vs Stretch Goals

Bu doküman boyunca her özellik şu etiketlerden biriyle işaretlidir:

| Etiket | Anlamı |
|---|---|
| 🟢 **MVP** | Mutlaka tamamlanmalı. Bu olmadan demo yapılamaz. |
| 🟡 **Stretch** | Zaman kalırsa eklenir. Demoda gösterilmezse jüri farkına varmaz. |

### 1.5. Kapsam Sınırları (Hard Scope)

Aşağıdaki sınırlar **kesin** ve geliştirme süresince genişletilmeyecek:

| Konu | Karar |
|---|---|
| **Desteklenen diller** | Python, JavaScript, TypeScript. Başka dilde repo gelirse "bu dil henüz desteklenmiyor" mesajı. |
| **Auth / kullanıcı sistemi** | YOK. Demo modu — herkes URL girip analiz başlatabilir. (İlerleyen sürümlerde eklenebilir.) |
| **Private repo desteği** | YOK. Sadece public GitHub repoları. Private gelirse 401 + "demo için public repo gerekli" mesajı. |
| **Repo boyutu** | Üst sınır 500MB clone. Üzerini reddet ama Tarihçi gibi ajanlarda akıllı özetleme yap (sınır değil, optimizasyon). |
| **Rate limit** | YOK — uyarı mekanizması var (Bölüm 13'e bak). |

---

## 2. Sistem Mimarisi

### 2.1. Üst Düzey Mimari

```
┌──────────────────────────────────────────────────────────────────┐
│                          KULLANICI                                │
│                  (GitHub URL girer / soru sorar)                  │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              FRONTEND (Next.js 14 — Vercel)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Tek Sayfa Interaktif Rapor                                 │  │
│  │  ┌─────────┬────────┬──────────┬──────────────────┐        │  │
│  │  │ Özet    │ Mimap  │ Timeline │ Repoyla Konuş    │        │  │
│  │  └─────────┴────────┴──────────┴──────────────────┘        │  │
│  │  [Canlı Progress Bar — WebSocket ile ajan durumu]          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │ REST API                     │ WebSocket
                  ▼                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              BACKEND API (FastAPI — Railway/Render)               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                                │  │
│  │   POST /analyze        — Yeni analiz başlat                │  │
│  │   GET  /analysis/{id}  — Analiz durumu/sonuç               │  │
│  │   POST /chat/{id}      — Repoyla sohbet                    │  │
│  │   WS   /progress/{id}  — Canlı ajan durumu                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                 │                                 │
│                                 │ enqueue                         │
│                                 ▼                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │           CELERY WORKER — Analiz Pipeline                  │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ AŞAMA 1: KAZI (Ingestion)                            │  │  │
│  │  │  • git clone                                         │  │  │
│  │  │  • tree-sitter ile AST parse                         │  │  │
│  │  │  • Fonksiyon/sınıf bazlı chunking                    │  │  │
│  │  │  • Gemini embedding API ile vektörleştirme           │  │  │
│  │  │  • Qdrant'a yazım                                    │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                            │                               │  │
│  │                            ▼                               │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ AŞAMA 2: PLAN AGENT (Üst Akıl)                       │  │  │
│  │  │  Repo özetini alır, hangi Skill ajanların            │  │  │
│  │  │  hangi sırayla çalışacağını belirler.                │  │  │
│  │  │  Çıktı: ROADMAP.md + execution plan JSON             │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                            │                               │  │
│  │           ┌────────────────┼────────────────┐              │  │
│  │           ▼                ▼                ▼              │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │  │
│  │  │ SKILL: MİMAR │ │SKILL:TARİHÇİ │ │SKILL:DEDEKTİF│        │  │
│  │  │ Yapı + bağ.  │ │ Git evrim    │ │ Teknik borç  │        │  │
│  │  │ (Gemini)     │ │ (Groq Llama) │ │ (Gemini)     │        │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │  │
│  │           └────────────────┬────────────────┘              │  │
│  │                            ▼                               │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ AŞAMA 3: ONBOARDING AGENT 🟡 (Sentezleyici)          │  │  │
│  │  │  3 ajanın çıktısını birleştirir, yeni geliştirici    │  │  │
│  │  │  için "ilk hafta yol haritası" üretir.               │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │           CHAT AGENT (RAG) — Async, kullanıcı sorduğunda   │  │
│  │   Soru → embedding → Qdrant retrieval → context →          │  │
│  │   Gemini → streaming cevap                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       VERİ KATMANI                                │
│   ┌──────────────┬───────────────┬──────────────────────────┐    │
│   │  PostgreSQL  │     Redis     │        Qdrant            │    │
│   │  Analiz      │  Celery broker│  Kod chunk vektörleri    │    │
│   │  sonuçları   │  + cache      │  (her repo bir koleksiyon)│   │
│   └──────────────┴───────────────┴──────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DIŞ SERVİSLER (Ücretsiz)                       │
│   • Gemini API (2.5 Flash + text-embedding-004)                  │
│   • Groq API (Llama 3.3 70B — yedek/hızlı)                       │
│   • GitHub API (repo metadata)                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2. Mimari Prensipler

**Asenkron işlem.** Repo analizi 1-5 dakika sürebilir. Frontend bunu beklememelidir; Celery worker arka planda çalışır, frontend WebSocket üzerinden ilerleme görür.

**Modüler ajan yapısı.** Her Skill ajanı bağımsız bir Python sınıfı; ortak `BaseAgent` arayüzünü implemente eder. Yeni ajan eklemek = yeni dosya açmak.

**Ölçeklenebilirlik.** Küçük repo da büyük repo da aynı pipeline'dan geçer. Fark sadece chunk sayısı ve LLM çağrı sayısıdır. Qdrant retrieval bunu sabit tutar.

**Cache-first.** Aynı repo iki kez analiz edilmez. SHA-1 hash + commit hash key olarak kullanılır.

**Fail-soft.** Bir ajan çökerse diğerleri çalışmaya devam eder. Kullanıcı "Tarihçi ajanı şu an çalışmıyor" görür ama uygulama kullanılabilir kalır.

---

## 3. İş Akış Şeması

### 3.1. Ana Kullanıcı Akışı

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Kullanıcı GitHub URL girer                                  │
│     [https://github.com/foo/bar]                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Frontend → POST /analyze                                    │
│     Backend doğrular, Celery task açar, analysis_id döner.      │
│     Frontend WebSocket'e bağlanır: /progress/{analysis_id}      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. KAZI AŞAMASI                          [WS: "Repo indiriliyor"] │
│     • git clone --depth=200                                     │
│     • Dil tespiti (linguist benzeri)                            │
│     • Dosya filtreleme (node_modules, .git, vb. atla)           │
│     • tree-sitter ile AST parse → fonksiyon/sınıf chunk'ları    │
│     • Gemini embedding ile vektörleştirme                       │
│     • Qdrant'a yazım                                            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. PLAN AGENT                            [WS: "Plan hazırlanıyor"] │
│     Input: dil, framework, dosya sayısı, klasör yapısı           │
│     Output: hangi ajanlar, hangi sırada, hangi sub-task'larla    │
│     ROADMAP.md ve execution_plan.json oluştur                   │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ MİMAR (paralel)  │ │TARİHÇİ(par.) │ │ DEDEKTİF (par.)  │
│ [WS: çalışıyor]  │ │[WS: çalışıyor]│ │[WS: çalışıyor]  │
│                  │ │              │ │                  │
│ • İmport graph   │ │• Önemli      │ │• Ölü kod         │
│ • Modül özetleri │ │  commitler   │ │• TODO/FIXME      │
│ • Mimari pattern │ │• Hot files   │ │• Bağımlılık riski│
│ • Tıklanabilir   │ │• Katkı       │ │• Güvenlik        │
│   Cytoscape JSON │ │  haritası    │ │  uyarıları       │
└──────────────────┘ └──────────────┘ └──────────────────┘
              └────────────────┬────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. ONBOARDING AGENT 🟡       [WS: "Yol haritası yazılıyor"]    │
│     Input: yukarıdaki 3 ajanın tüm çıktıları                    │
│     Output: "İlk hafta için yapman gerekenler" listesi          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. SONUÇ DEPOLAMA                        [WS: "Tamamlandı"]    │
│     PostgreSQL'e analysis_result yazılır.                       │
│     Frontend WebSocket sonucu alır → sayfayı render eder.       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. KULLANICI ETKİLEŞİMİ                                        │
│     • Sekmeler arası geçiş (Özet / Mimap / Timeline / Chat)     │
│     • Mimap'ta düğüme tıklama → detay paneli                    │
│     • Chat: soru sorar → RAG → cevap stream                     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2. Chat Akışı (RAG) 🟡

```
Kullanıcı sorusu: "Auth nasıl çalışıyor?"
        │
        ▼
[1] Query embedding (Gemini text-embedding-004)
        │
        ▼
[2] Qdrant retrieval — top 8 chunk
        │
        ▼
[3] Re-ranking: vektör skor + dosya yolu skoru harmanlama
        │
        ▼
[4] Context oluştur:
    • Top 5 kod chunk (kaynak dosya yolu ile)
    • Mimar ajanın "auth" modülü için yazdığı özet (varsa)
    • Dedektif ajanın bu modüle dair uyarıları (varsa)
        │
        ▼
[5] Gemini 2.5 Flash → streaming cevap
        │
        ▼
[6] Frontend cevabı stream eder + altta kaynak chunk'ları gösterir
    (tıklanırsa kod açılır — "kanıt" katmanı)
```

### 3.3. Hata ve Kenar Durum Akışları

| Durum | Davranış |
|---|---|
| Repo private veya bulunamadı | 404 dön, frontend hatayı göster |
| Repo > 500MB | 413 dön, "Çok büyük repo, demo için lütfen küçük bir repo seçin" |
| Bir Skill ajan timeout | Diğer ajanlar devam eder, sonuçta "ajan başarısız" işareti |
| LLM rate limit | Exponential backoff + Groq'a fallback |
| Qdrant erişilemiyor | Chat devre dışı, diğer sayfalar çalışır |
| Aynı repo daha önce analiz edildi | Cache'den dön, "Önceki analiz: X dakika önce" göster |

---

## 4. Teknoloji Yığını ve Gerekçeler

### 4.1. Frontend

| Teknoloji | Versiyon | Neden? |
|---|---|---|
| **Next.js** | 14 (App Router) | SSR + API route + hızlı setup |
| **TypeScript** | 5.x | Type safety, hackathon'da bug azaltır |
| **TailwindCSS** | 3.x | Hızlı styling |
| **shadcn/ui** | latest | Hazır, güzel komponentler — Card, Tabs, Dialog vb. |
| **Cytoscape.js** | 3.x | Mimari grafiği için en iyi seçim (Mermaid statik) |
| **vis-timeline** | 7.x | Timeline için olgun kütüphane |
| **Vercel AI SDK** | latest | `useChat` hook ile streaming chat hazır |
| **Socket.IO Client** | 4.x | Canlı ilerleme için WebSocket |
| **react-syntax-highlighter** | latest | Chat'te kod gösterimi |

### 4.2. Backend

| Teknoloji | Neden? |
|---|---|
| **Python 3.11+** | AI ekosistemi |
| **FastAPI** | Async + otomatik OpenAPI doc + Pydantic |
| **Celery** | Uzun süreli task'lar için endüstri standardı |
| **Redis** | Celery broker + cache |
| **PostgreSQL 16** | Analiz sonuçları + ilişkisel veri |
| **SQLAlchemy 2.x** + **Alembic** | ORM + migration |
| **Pydantic v2** | Validasyon, FastAPI ile entegre |

### 4.3. AI Katmanı

| Servis | Kullanım | Maliyet |
|---|---|---|
| **Gemini 2.5 Flash** | Plan Agent, Mimar, Dedektif, Onboarding, Chat | Ücretsiz tier (15 RPM, 1M TPM) |
| **Gemini text-embedding-004** | Kod chunk embedding | Ücretsiz tier |
| **Groq Llama 3.3 70B** | Tarihçi ajan + fallback | Ücretsiz tier (30 RPM) |
| **Qdrant** | Vektör DB | Self-hosted Docker, ücretsiz |

> **Not:** Gemini'nin ücretsiz tier'ı 15 RPM. Bu yüzden ajanlar **paralel değil, sıralı** çalıştırılacak (Plan → [Mimar, Dedektif aynı anda] → Tarihçi → Onboarding). Tarihçi'yi Groq'a verince paralelleştirme imkanı doğar.

### 4.4. Kod Analizi Araçları

| Araç | Görev |
|---|---|
| **GitPython** | Repo klonlama, git log okuma |
| **tree-sitter** + dil grammarları (py, js, ts, go, java) | Çok dilli AST parse |
| **ruff** | Python lint/static analysis |
| **eslint** | JS/TS lint (subprocess çağrısıyla) |
| **radon** | Karmaşıklık metrikleri (Python) |
| **vulture** | Ölü kod tespiti (Python) |

### 4.5. Deploy

| Bileşen | Yer |
|---|---|
| Frontend | Vercel (free tier) |
| Backend API + Worker | Railway veya Render (free tier) |
| PostgreSQL | Railway built-in |
| Redis | Railway built-in |
| Qdrant | Railway Docker deploy |

---

## 5. Veri Modelleri

### 5.1. PostgreSQL Şeması

```python
# backend/app/models.py

from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey
from datetime import datetime
import uuid

Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_url: Mapped[str] = mapped_column(String(500), index=True)
    repo_hash: Mapped[str] = mapped_column(String(64), index=True)  # cache key
    commit_sha: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))  # pending|running|done|failed
    progress: Mapped[dict] = mapped_column(JSON, default=dict)  # {"miner":"done", "mimar":"running", ...}

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
    sources: Mapped[list | None] = mapped_column(JSON)  # retrieved chunk metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### 5.2. Qdrant Koleksiyon Şeması

Her analiz için ayrı koleksiyon: `repo_{analysis_id}`

```python
# Vektör boyutu: 768 (text-embedding-004)
# Distance: COSINE

# Payload (chunk metadata):
{
    "file_path": "src/auth/login.py",
    "start_line": 42,
    "end_line": 87,
    "chunk_type": "function",  # function|class|module
    "name": "authenticate_user",
    "language": "python",
    "code": "def authenticate_user(...): ...",  # ham kod
    "last_modified": "2024-03-15T...",
    "last_author": "alice@example.com",
}
```

### 5.3. Pydantic Şemaları (API)

```python
# backend/app/schemas.py

from pydantic import BaseModel, HttpUrl
from typing import Literal

class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl
    branch: str = "main"

class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str

class ProgressUpdate(BaseModel):
    analysis_id: str
    stage: Literal["mining", "planning", "mimar", "tarihci", "dedektif", "onboarding", "done", "error"]
    message: str
    progress_pct: int  # 0-100

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    content: str
    sources: list[dict]
```

---

## 6. API Sözleşmesi

### 6.1. REST Endpoint'leri

#### `POST /api/analyze`
Yeni analiz başlatır.

**Request:**
```json
{ "repo_url": "https://github.com/foo/bar", "branch": "main" }
```

**Response (202 Accepted):**
```json
{ "analysis_id": "uuid", "status": "pending" }
```

**Hatalar:** 400 (geçersiz URL), 404 (repo bulunamadı), 413 (repo çok büyük), 429 (rate limit).

---

#### `GET /api/analysis/{analysis_id}`
Analiz durumu ve sonucu döner.

**Response (200):**
```json
{
  "analysis_id": "uuid",
  "status": "done",
  "progress": { "mimar": "done", "tarihci": "done", "dedektif": "done", "onboarding": "done" },
  "results": {
    "summary": { ... },
    "architecture_graph": { "nodes": [...], "edges": [...] },
    "timeline": [...],
    "health_report": {...},
    "onboarding_guide": {...}
  }
}
```

---

#### `POST /api/chat/{analysis_id}` 🟡
Repoyla sohbet. **Streaming response** (Server-Sent Events).

**Request:**
```json
{ "message": "Auth nasıl çalışıyor?" }
```

**Response (text/event-stream):**
```
data: {"type":"sources","sources":[{"file":"auth/login.py","lines":"42-87"}]}
data: {"type":"chunk","content":"Auth sistemi "}
data: {"type":"chunk","content":"JWT tabanlı..."}
data: {"type":"done"}
```

---

### 6.2. WebSocket: `/ws/progress/{analysis_id}`

Sunucu → İstemci mesajları:
```json
{
  "stage": "mimar",
  "message": "Mimar ajanı modül bağımlılıklarını çözümlüyor...",
  "progress_pct": 45
}
```

---

## 7. Modül Modül Geliştirme Rehberi

### 7.1. Klasör Yapısı

```
repoarkeolog/
├── frontend/                       # Next.js 14
│   ├── app/
│   │   ├── page.tsx                # Landing — URL input
│   │   ├── analysis/[id]/page.tsx  # Analiz sonuç sayfası
│   │   └── api/                    # Client-side API helpers
│   ├── components/
│   │   ├── tabs/
│   │   │   ├── SummaryTab.tsx
│   │   │   ├── MimapTab.tsx        # Cytoscape
│   │   │   ├── TimelineTab.tsx     # vis-timeline
│   │   │   └── ChatTab.tsx         # Vercel AI SDK
│   │   ├── ProgressBar.tsx         # WebSocket dinler
│   │   └── ui/                     # shadcn
│   └── lib/
│       ├── api.ts
│       └── socket.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── api/
│   │   │   ├── analyze.py          # /analyze, /analysis/{id}
│   │   │   ├── chat.py             # /chat/{id}
│   │   │   └── ws.py               # /ws/progress/{id}
│   │   ├── models.py               # SQLAlchemy
│   │   ├── schemas.py              # Pydantic
│   │   ├── db.py                   # DB session
│   │   ├── config.py               # Pydantic Settings
│   │   ├── tasks/
│   │   │   ├── celery_app.py
│   │   │   └── analyze_task.py     # Ana orkestratör
│   │   ├── pipeline/
│   │   │   ├── miner.py            # Klonlama + chunking + embedding
│   │   │   ├── chunker.py          # tree-sitter wrapper
│   │   │   └── embedder.py         # Gemini embedding
│   │   ├── agents/
│   │   │   ├── base.py             # BaseAgent ABC
│   │   │   ├── plan_agent.py
│   │   │   ├── mimar_agent.py
│   │   │   ├── tarihci_agent.py
│   │   │   ├── dedektif_agent.py
│   │   │   └── onboarding_agent.py
│   │   ├── llm/
│   │   │   ├── gemini.py
│   │   │   └── groq.py
│   │   ├── rag/
│   │   │   ├── retriever.py        # Qdrant arama
│   │   │   └── chat_chain.py       # RAG zinciri
│   │   └── utils/
│   │       ├── github.py
│   │       └── progress.py         # WebSocket emitter
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
│
├── infra/
│   ├── docker-compose.yml          # Lokal dev: postgres, redis, qdrant
│   └── Dockerfile.backend
│
├── ARCHITECTURE.md                 # Plan Agent çıktısı (şartname)
├── ROADMAP.md                      # Plan Agent çıktısı (şartname)
├── developer.md                    # bu doküman
└── README.md
```

### 7.2. BaseAgent Arayüzü

Tüm Skill ajanları aynı arayüzü uygular:

```python
# backend/app/agents/base.py

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class AgentContext(BaseModel):
    analysis_id: str
    repo_path: str  # lokal klon yolu
    repo_metadata: dict  # dil, framework, dosya sayısı vs.
    plan: dict  # Plan Agent'ın çıktısı
    previous_outputs: dict  # önceki ajanların sonuçları


class BaseAgent(ABC):
    name: str  # "mimar", "tarihci", vb.

    @abstractmethod
    async def run(self, ctx: AgentContext) -> dict:
        """
        Ajan ana mantığı. Pydantic ile validate edilmiş JSON döner.
        Hata durumunda exception fırlatır; orchestrator handle eder.
        """
        ...

    async def emit_progress(self, ctx: AgentContext, message: str, pct: int):
        """WebSocket'e ilerleme yayar."""
        from app.utils.progress import push_progress
        await push_progress(ctx.analysis_id, self.name, message, pct)
```

### 7.3. Orkestratör (Celery Task)

```python
# backend/app/tasks/analyze_task.py

from app.tasks.celery_app import celery_app
from app.pipeline.miner import mine_repo
from app.agents.plan_agent import PlanAgent
from app.agents.mimar_agent import MimarAgent
from app.agents.tarihci_agent import TarihciAgent
from app.agents.dedektif_agent import DedektifAgent
from app.agents.onboarding_agent import OnboardingAgent
from app.agents.base import AgentContext
from app.db import SessionLocal
from app.models import Analysis
import asyncio


@celery_app.task(bind=True)
def analyze_repo_task(self, analysis_id: str, repo_url: str):
    asyncio.run(_run(analysis_id, repo_url))


async def _run(analysis_id: str, repo_url: str):
    db = SessionLocal()
    try:
        # 1. Mining
        repo_path, metadata = await mine_repo(analysis_id, repo_url)

        ctx = AgentContext(
            analysis_id=analysis_id,
            repo_path=repo_path,
            repo_metadata=metadata,
            plan={},
            previous_outputs={},
        )

        # 2. Plan Agent
        plan = await PlanAgent().run(ctx)
        ctx.plan = plan
        _save_field(db, analysis_id, "plan_output", plan)

        # 3. Skill ajanları (sırayla — rate limit için)
        for agent_cls, field in [
            (MimarAgent, "mimar_output"),
            (TarihciAgent, "tarihci_output"),
            (DedektifAgent, "dedektif_output"),
        ]:
            try:
                output = await agent_cls().run(ctx)
                ctx.previous_outputs[agent_cls.name] = output
                _save_field(db, analysis_id, field, output)
            except Exception as e:
                _save_field(db, analysis_id, field, {"error": str(e)})

        # 4. Onboarding (opsiyonel — stretch)
        try:
            onboarding = await OnboardingAgent().run(ctx)
            _save_field(db, analysis_id, "onboarding_output", onboarding)
        except Exception:
            pass

        # 5. Tamamlandı
        _mark_done(db, analysis_id)
    except Exception as e:
        _mark_failed(db, analysis_id, str(e))
    finally:
        db.close()
```

> Helper fonksiyonların (`_save_field`, `_mark_done`, vb.) implementasyonu basit DB UPDATE'leridir; geliştirici yazacak.

### 7.4. Mining Pipeline (en kritik kısım)

```python
# backend/app/pipeline/miner.py

import git
import tempfile
from pathlib import Path
from app.pipeline.chunker import chunk_repo
from app.pipeline.embedder import embed_chunks
from app.utils.progress import push_progress


async def mine_repo(analysis_id: str, repo_url: str) -> tuple[str, dict]:
    await push_progress(analysis_id, "mining", "Repo indiriliyor...", 5)

    tmp_dir = tempfile.mkdtemp()
    repo = git.Repo.clone_from(repo_url, tmp_dir, depth=200)

    metadata = _extract_metadata(repo, tmp_dir)

    await push_progress(analysis_id, "mining", "Kod parse ediliyor...", 15)
    chunks = chunk_repo(tmp_dir)  # tree-sitter

    await push_progress(analysis_id, "mining", "Embedding hesaplanıyor...", 25)
    await embed_chunks(analysis_id, chunks)  # Gemini → Qdrant

    await push_progress(analysis_id, "mining", "Kazı tamamlandı.", 30)
    return tmp_dir, metadata


def _extract_metadata(repo: git.Repo, path: str) -> dict:
    """Dil tespiti, dosya sayısı, framework hint, vs."""
    files = list(Path(path).rglob("*"))
    # ... (geliştirici detayı yazacak)
    return {
        "languages": ...,
        "file_count": ...,
        "primary_language": ...,
        "frameworks": [...],
        "commit_count": len(list(repo.iter_commits())),
        "contributors": len(set(c.author.email for c in repo.iter_commits())),
    }
```

---

## 8. AI Ajan Tasarımı ve Prompt'lar

### 8.1. Plan Agent

**Görev:** Repo metadata'sını alır, hangi Skill ajanların hangi sırayla, hangi alt görevlerle çalışacağını belirler.

**Sistem prompt'u:**

```
Sen bir senior yazılım mimarısın. Görevin: verilen repo metadata'sına bakarak,
3 uzman ajanın (Mimar, Tarihçi, Dedektif) yapacağı analizleri planlamak.

Çıktın saf JSON olmalı, şu yapıda:
{
  "summary": "Bu repo X teknolojisiyle yazılmış Y türünde bir projedir.",
  "agent_plan": {
    "mimar": {
      "sub_tasks": ["...", "..."],
      "focus_areas": ["src/auth", "src/api"],
      "expected_output": "..."
    },
    "tarihci": {
      "sub_tasks": [...],
      "interesting_periods": ["last_6_months", "initial_commits"]
    },
    "dedektif": {
      "sub_tasks": [...],
      "priority_checks": ["security", "dead_code"]
    }
  },
  "estimated_complexity": "low|medium|high"
}

Sadece JSON dön, başka metin yazma.
```

**User prompt:** Repo metadata JSON'ı.

**Çıktı kullanımı:** `ROADMAP.md` olarak repo'ya yazılır (şartname gereği) + execution plan olarak ajanlara aktarılır.

### 8.2. Mimar Ajan 🟢

**Görev:** Mimari haritası, modül bağımlılıkları, tasarım pattern'ları çıkarır.

**Pipeline:**
1. Tree-sitter ile import/include statement'larını topla
2. Modül bağımlılık grafiğini kur (NetworkX)
3. Klasör yapısını + bağımlılık grafiğini Gemini'ye yolla
4. Gemini her ana modül için kısa açıklama ve genel mimari pattern üretir

**Sistem prompt'u:**

```
Sen bir senior software architect'sin. Sana bir projenin klasör yapısı ve
modül bağımlılık grafiği verilecek. Görevin:

1. Üst düzey mimari pattern'ı tespit et (MVC, monorepo, mikroservis, layered, vb.)
2. Her ana modülün bir cümlelik amacını yaz
3. Dikkat çekici bağımlılıklar veya circular dependencies varsa belirt

Çıktı saf JSON:
{
  "architecture_pattern": "...",
  "modules": [
    {
      "path": "src/auth",
      "purpose": "...",
      "depends_on": ["src/db", "src/utils"],
      "dependents": ["src/api"]
    }
  ],
  "warnings": ["..."]
}
```

**Frontend için ek çıktı:** Cytoscape.js node/edge JSON'ı.

### 8.3. Tarihçi Ajan 🟢

**Görev:** Git geçmişinden projenin "evrim hikayesini" çıkarır.

**Pipeline:**
1. `git log --stat` ile commit geçmişini oku
2. Sıkça değişen dosyaları (hot files) tespit et
3. Büyük commit'leri (>500 satır değişiklik) veya merge'leri öne çıkar
4. Katkıda bulunanların commit dağılımını çıkar
5. **Akıllı seçim** uygula (aşağıda) → token sınırı içinde kalan bir özet hazırla
6. Bunları Llama'ya (Groq) yolla, hikaye oluştur

#### Akıllı Commit Seçim Stratejisi

LLM'e *tüm* commit'leri yollamak token limitini aşar (5000 commitlik bir repoda ~500k token). Onun yerine:

```python
def select_significant_commits(repo, max_commits: int = 150) -> list:
    """
    Tüm commit sayısı max_commits'ten azsa hepsini al.
    Aksi halde 'önemli' commit'leri seç:
      - İlk 10 commit (proje başlangıcı)
      - Son 30 commit (yakın aktivite)
      - Diff boyutu top %10 olan commit'ler (büyük değişiklikler)
      - Tüm merge commit'leri
      - Her ay başından 1 commit (zaman dağılımı)
    Sonra deduplicate edip kronolojik sırala.
    """
    all_commits = list(repo.iter_commits())
    if len(all_commits) <= max_commits:
        return all_commits

    selected = set()
    selected.update(all_commits[-10:])              # ilk 10 (en eski)
    selected.update(all_commits[:30])               # son 30 (en yeni)
    selected.update(c for c in all_commits if len(c.parents) > 1)  # merge'ler

    # Büyük diff'li olanlar (insertion + deletion)
    by_size = sorted(all_commits,
                     key=lambda c: c.stats.total["lines"],
                     reverse=True)
    selected.update(by_size[:max_commits // 5])

    # Aylık örnekleme
    selected.update(_monthly_samples(all_commits))

    return sorted(selected, key=lambda c: c.committed_date)[:max_commits]
```

**Kullanıcı uyarısı:** Eğer akıllı seçim devreye girerse, sonuçta `summary_note` alanına ekle:
```json
{ "summary_note": "Bu repo 4200 commit içeriyor — Tarihçi temsili 150 commit üzerinden hikaye çıkardı." }
```
Frontend bunu gösterecek, jüri "neden 4200 commit yokmuş?" diye sormaz.

**Sistem prompt'u:**

```
Sen yazılım tarihçisisin. Sana bir projenin commit istatistikleri verilecek.
Görevin: bu projenin evrim hikayesini timeline olarak çıkarmak.

Çıktı saf JSON:
{
  "story_summary": "Proje 2022'de başladı, ilk 6 ay X üzerine yoğunlaştı...",
  "milestones": [
    {
      "date": "2023-04-15",
      "commit_sha": "abc123",
      "title": "Auth katmanı eklendi",
      "description": "Bu noktada proje monolit yapıdan ayrılmaya başladı."
    }
  ],
  "hot_files": [
    {"path": "src/api.py", "change_count": 47, "note": "En sık değişen dosya"}
  ],
  "contributor_summary": {
    "total": 8,
    "active_last_3_months": 3
  }
}
```

### 8.4. Dedektif Ajan 🟢

**Görev:** Teknik borç, ölü kod, güvenlik uyarıları, eski paketler.

**Pipeline:**
1. `ruff check` (Python) veya `eslint` (JS/TS) çalıştır → çıktıyı parse et
2. `vulture` ile ölü kod ara (Python)
3. TODO/FIXME/HACK yorumlarını grep'le
4. `package.json` / `requirements.txt` paketlerinin yaşını kontrol et
5. Tüm bulguları Gemini'ye yolla, önemlilik sıralaması yapsın

**Sistem prompt'u:**

```
Sen bir code review uzmanısın. Sana bir projenin static analysis bulguları
verilecek. Görevin: bunları önceliklendirip "sağlık karnesi" üretmek.

Çıktı saf JSON:
{
  "health_score": 72,
  "summary": "Genel olarak temiz, ama X modülünde teknik borç birikmiş.",
  "issues": [
    {
      "severity": "high|medium|low",
      "category": "security|dead_code|tech_debt|outdated_dep",
      "title": "...",
      "description": "...",
      "file_path": "...",
      "line_range": [42, 87]
    }
  ],
  "stats": {
    "todos": 23,
    "dead_functions": 5,
    "outdated_deps": 12
  }
}
```

### 8.5. Onboarding Ajan 🟡

**Görev:** Diğer 3 ajanın çıktısını sentezler, yeni geliştirici için "ilk hafta yol haritası" üretir.

**Sistem prompt'u:**

```
Sen experienced bir tech lead'sın. Sana bir projenin mimari analizi, tarihi
ve sağlık raporu verilecek. Bu projeye yeni katılan bir geliştirici için
"ilk hafta yol haritası" hazırla.

Çıktı saf JSON:
{
  "intro": "Bu projeye hoş geldin! Burası X yapan bir Y projesi.",
  "day_1": ["README oku", "Şu modülü incele: ..."],
  "day_2": [...],
  "day_3": [...],
  "first_pr_suggestion": {
    "title": "...",
    "rationale": "Bu küçük issue, kodbase'i tanıman için ideal."
  },
  "people_to_ask": [
    {"name": "Alice", "expertise": "auth modülü", "from_commits": true}
  ]
}
```

### 8.6. Chat Agent (RAG) 🟡

**Sistem prompt'u:**

```
Sen bu repo hakkında soruları yanıtlayan bir asistansın. Aşağıda repodan
ilgili kod parçaları ve önceki analizlerden ilgili özetler var. Bu bağlamı
kullanarak kullanıcının sorusunu yanıtla.

KURAL: Sadece verilen bağlamdan yararlan. Bağlamda olmayan şey için
"Bu repoda bu konuda bilgi bulamadım" de.

Cevap dilini kullanıcının diline uydur.
```

**Context oluşturma:**
```python
context = f"""
İLGİLİ KOD PARÇALARI:
{retrieved_chunks_formatted}

İLGİLİ MİMARİ BİLGİSİ:
{mimar_output_relevant_module}

İLGİLİ TEKNİK BORÇLAR:
{dedektif_output_relevant_findings}
"""
```

---

## 9. Frontend Geliştirme Rehberi

### 9.1. Sayfa Yapısı

**`/`** — Landing
- Büyük bir input: "GitHub URL gir"
- Alt: "Demo için: github.com/foo/bar" gibi 3 örnek (önceden cache'li)
- Submit → `/analysis/{id}`'ye yönlendir

**`/analysis/[id]`** — Tek sayfa rapor
- Üstte: Repo başlığı + sağlık skoru rozeti
- WebSocket bağlı, ilerleme bar'ı (analiz devam ederken)
- Tabs (shadcn): Özet | Mimap | Timeline | Chat 🟡

### 9.2. Mimap (Cytoscape) Implementasyon İpuçları

```typescript
// components/tabs/MimapTab.tsx
import CytoscapeComponent from "react-cytoscapejs";

export function MimapTab({ data }: { data: MimarOutput }) {
  const elements = data.modules.flatMap((m) => [
    { data: { id: m.path, label: m.path.split("/").pop(), purpose: m.purpose } },
    ...m.depends_on.map((dep) => ({
      data: { source: m.path, target: dep },
    })),
  ]);

  return (
    <CytoscapeComponent
      elements={elements}
      layout={{ name: "cose", animate: true, idealEdgeLength: () => 100 }}
      stylesheet={[
        { selector: "node", style: { label: "data(label)", "background-color": "#0ea5e9" } },
        { selector: "edge", style: { "curve-style": "bezier", "target-arrow-shape": "triangle" } },
      ]}
      cy={(cy) => {
        cy.on("tap", "node", (evt) => openDetailPanel(evt.target.data()));
      }}
    />
  );
}
```

**Önemli:** 200+ düğüm varsa otomatik klasör seviyesinde grupla. `compound nodes` kullan.

### 9.3. Chat (Vercel AI SDK)

```typescript
// components/tabs/ChatTab.tsx
import { useChat } from "ai/react";

export function ChatTab({ analysisId }: { analysisId: string }) {
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: `/api/chat-proxy?analysisId=${analysisId}`, // Backend'e proxy
  });

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto">
        {messages.map((m) => (
          <Message key={m.id} role={m.role} content={m.content} sources={m.data?.sources} />
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} placeholder="Repo hakkında soru sor..." />
      </form>
    </div>
  );
}
```

**Kaynak chunk'ları gösterimi:** Her assistant cevabının altında "Kaynaklar" accordion'u — tıklanırsa kod gösterilir (`react-syntax-highlighter`).

### 9.4. Progress Bar (WebSocket)

```typescript
// components/ProgressBar.tsx
import { useEffect, useState } from "react";

export function ProgressBar({ analysisId }: { analysisId: string }) {
  const [progress, setProgress] = useState({ stage: "starting", pct: 0, message: "" });

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/progress/${analysisId}`);
    ws.onmessage = (e) => setProgress(JSON.parse(e.data));
    return () => ws.close();
  }, [analysisId]);

  return (
    <div>
      <div className="text-sm">{progress.message}</div>
      <div className="h-2 bg-gray-200 rounded">
        <div className="h-full bg-blue-500" style={{ width: `${progress.pct}%` }} />
      </div>
    </div>
  );
}
```

---

## 10. GitHub Akışı ve Şartname Uyumluluğu

### 10.1. Branch Stratejisi (GitHub Flow)

- `main` — sadece çalışan, dağıtıma hazır kod. Direkt push **yasak**.
- `feature/<görev-adı>` — her yeni özellik için
- `fix/<hata-adı>` — hata düzeltme

### 10.2. Commit Mesaj Standardı

Conventional Commits:
```
feat: add mimar agent prompt
fix: handle empty repo case in miner
chore: update dependencies
docs: add agent design rationale
refactor: extract chunker to separate module
```

### 10.3. PR Süreci

1. Feature branch'te çalış
2. PR aç, açıklamada **"AI Traceability"** bölümü olsun:
   ```markdown
   ## AI Traceability
   - Plan Agent: bu görevin sub-task'larını şu prompt ile çıkardı: ...
   - Skills Agent (Refactoring): şu fonksiyonu optimize etti: ...
   ```
3. Repo Maintainer review eder, en az bir takım üyesi onay verir → merge
4. Merge stratejisi: **squash merge**

### 10.4. GitHub Issues

Her sub-task = bir Issue.
- Şablon: `[<modül>] <kısa açıklama>`
- Label'lar: `frontend`, `backend`, `agent`, `infra`, `bug`, `enhancement`
- Atanma: Plan Agent çıktısındaki rol dağılımına göre

### 10.5. Şartname Çıktıları (Repo'ya zorunlu)

| Dosya | İçerik | Ne zaman |
|---|---|---|
| `ARCHITECTURE.md` | Sistem mimarisi (bu dokümanın özeti) | İlk geliştirme saatlerinde |
| `ROADMAP.md` | Plan Agent çıktısı | Plan Agent task'ı çalıştığında otomatik |
| `developer.md` | Bu doküman | Hackathon başında repoda hazır |
| `README.md` | Kurulum + demo URL | Teslimden önce |

### 10.6. AI Traceability — Kod Yorumları

Skills Agent'ın dokunduğu her yerin başına yorum:

```python
# AI-OPTIMIZED by Skills Agent (Refactoring)
# Original: nested loop with O(n^2)
# Refactored: dict lookup, O(n)
def find_dependencies(modules: list, target: str) -> list:
    ...
```

### 10.7. Final Review (Şartname gereği)

Teslimden önce tüm kod **Skills Agent (Refactoring)** ile taranır. Bu, Cursor/Claude Code'a "tüm projeyi gözden geçir, performans ve okunabilirlik açısından öneriler sun" diyerek yapılır. Önerilen değişiklikler ayrı bir PR'a açılır, takım üyesi onaylar, merge edilir.

---

---

## 11. Test Stratejisi

### 11.1. Birim Testleri (Şartname gereği)

Her modül için pytest:

```python
# backend/tests/test_chunker.py
def test_python_function_chunking():
    code = "def foo(): pass\ndef bar(): pass"
    chunks = chunk_python_code(code, "test.py")
    assert len(chunks) == 2
    assert chunks[0].name == "foo"
```

Kapsama hedefi: ajanlar için %50+, pipeline için %70+.

### 11.2. Entegrasyon Testleri

Bir "altın repo" hazırla (örn. küçük bir Flask app), uçtan uca test:

```python
def test_full_pipeline_on_golden_repo(golden_repo_url):
    analysis_id = start_analysis(golden_repo_url)
    wait_for_done(analysis_id, timeout=120)
    result = get_analysis(analysis_id)
    assert result.mimar_output["modules"]
    assert result.tarihci_output["milestones"]
    assert result.dedektif_output["health_score"] >= 0
```

### 11.3. Manuel Test Listesi (Demo Öncesi)

- [ ] Boş repo → düzgün hata mesajı
- [ ] Çok büyük repo → 413 hata
- [ ] Geçersiz URL → 400 hata
- [ ] Ajan timeout → diğer ajanlar çalışmaya devam ediyor
- [ ] Aynı repo iki kez → cache'den dönüyor
- [ ] Mimap'ta düğüme tıklama → detay paneli açılıyor
- [ ] Chat'te kaynak chunk'ları tıklanabiliyor
- [ ] WebSocket progress canlı güncelleniyor
- [ ] Mobile görünüm bozulmuyor

---

## 12. Demo Hazırlığı ve Risk Yönetimi

### 12.1. Demo Ortamı

- **Format:** Sahne + projeksiyon
- **Süre:** 3-5 dakika (esnek; her iki versiyon hazır olmalı)
- **İnternet:** Takım kendi mobil hotspot'unu kullanacak (mekan wifi'sine güvenme)
- **Yedek cihaz:** Demoyu sunan cihazın yanında **2. bir laptop** açık ve sisteme bağlı dursun (cihaz çökerse kayıpsız geçiş)

### 12.2. Demo Repoları

**Birincil demo (ana akış):**
- Takımın **kendi RepoArkeolog reposu**. Meta wow faktörü: "Aracımız kendisini analiz ediyor."
- Demo öncesi cache'lenmiş olmalı — analiz canlı görünür ama sonuçlar saniyeler içinde gelir.

**Yedek/opsiyonel demolar:**
- Küçük popüler bir repo (örn. `pallets/flask`, küçük bir branch) — jüri "başka bir repo deneyin" derse hazır
- Orta boyutlu bir repo — sadece istek gelirse, önceden cache'lenmemişse risk
- "Jüri kendi URL'sini girerse?" — kabul et ama "bu canlı çalışacak, biraz sürecek" diye uyar; başarısız olursa bile sorun yok çünkü demonun ana akışı zaten tamamlanmış olur

> **Strateji:** Demo başında "ana repomuzu göstereceğim, sonra dilerseniz başka repo da deneriz" de. Bu seni hem güvene alır hem esnek görünmen sağlar.

### 12.3. Demo Akışı (3 Dakikalık Versiyon)

| Süre | Ne |
|---|---|
| 0:00-0:15 | Açılış cümlesi + problem (yeni dev'in 2 hafta keşif yapması) |
| 0:15-0:30 | URL gir, "Analiz başla" → progress canlı akıyor (jüri ajanları izliyor!) |
| 0:30-1:30 | Sonuç sayfası — Özet, Mimap (düğüm tıkla, detay aç), Timeline |
| 1:30-2:30 | 🟡 Chat: "Auth nasıl çalışıyor?" → cevap stream + kaynak chunk'ları |
| 2:30-3:00 | Kapanış: AI Traceability göster (Plan Agent ROADMAP.md, Skills yorumları) |

### 12.4. Demo Akışı (5 Dakikalık Versiyon)

3 dakikalık akışa şunlar eklenir:
- **3:00-3:45** — Mimap'ta zoom in/out, daha detaylı modül incelemesi
- **3:45-4:30** — Chat'te 2. soru ("Bu projede en son ne değişti?")
- **4:30-5:00** — "Şartname uyumu" mini turu: GitHub'da PR'lar, Issue'lar, ROADMAP.md

### 12.5. Risk Tablosu

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| Gemini rate limit | Yüksek | Yüksek | Caching + Groq fallback + sıralı ajan + demo cache |
| Qdrant Docker'da çökerse | Düşük | Yüksek | Demo öncesi healthcheck + yedek dump + Qdrant Cloud yedek |
| Cytoscape büyük repoda donar | Orta | Orta | 200+ düğümde otomatik klasör grupla |
| Demo'da network düşer | Düşük | Çok yüksek | Mobil hotspot + 2. cihaz + lokal cache |
| Chat halüsinasyon | Yüksek | Orta | Sadece RAG context, "bilmiyorum" demeyi promptla zorla |
| Bir ajan hiç çalışmaz | Orta | Orta | Fail-soft: diğer ajanlar görünür, başarısız ajan "bakım modunda" |
| Projeksiyon çözünürlüğü uyumsuz | Orta | Düşük | UI 1280x720'de test edilmiş olsun |

### 12.6. "Korkutucu" Kenar Durumlar (Jüri Test Eder)

- Jüri tuhaf URL girerse (boş, gibberish, başka bir site) → düzgün hata
- Jüri **private repo URL'si** girerse → 401 + "demo modunda yalnızca public repo destekleniyor"
- Jüri **Java/Go/Rust** repo girerse → "şu an Python/JS/TS destekliyoruz" mesajı
- Jüri çok büyük bir repo girerse → 413 + "demo için <500MB" mesajı + alternatif öner
- Jüri "sen Anthropic değil misin?" diye sorarsa → "Açık ekosistem kullanıyoruz, Gemini + Llama"
- Jüri "hangi LLM kullanıyorsunuz?" diye sorarsa → "Gemini 2.5 Flash ana iş için, Groq Llama yedek/hızlı görevler için"

---

## 13. Maliyet ve Kaynak Yönetimi

### 13.1. Hedef: Sıfır veya Minimal Maliyet

Tüm servisler ücretsiz tier kullanılarak çalışacak şekilde tasarlandı:

| Servis | Ücretsiz Tier Limiti | Tahmini Tüketim (demo gününe) | Risk |
|---|---|---|---|
| Gemini API (LLM + embedding) | 15 RPM, 1M TPM, 1500 RPD | ~50-100 req | Düşük |
| Groq API | 30 RPM | ~10-30 req | Düşük |
| Vercel | Hobby tier sınırsız trafik | Önemsiz | Yok |
| Railway | $5 kredi/ay (yeni hesap) | ~$2-3 | Düşük |
| Qdrant Cloud (opsiyonel) | 1GB ücretsiz | <100MB | Yok |
| GitHub | Sınırsız public repo | Yok | Yok |

### 13.2. Gerekirse Ödemeli Upgrade

Aşağıdaki durumlarda **küçük bir ödeme** kabul:

| Durum | Çözüm | Tahmini Maliyet |
|---|---|---|
| Railway $5 krediyi aşarsa | Pay-as-you-go aktif et | $5-10/ay |
| Gemini ücretsiz tier dolarsa | Tier 1'e geç | ~$1-5 demo süresince |
| Demo günü ek hız gerekirse | OpenAI/Anthropic kredisiyle Sonnet 4 / GPT-4o-mini ekle | $5-10 |

> **Karar kuralı:** Demo gününden 24 saat önce, her iki ödeme limitini de hazır tut (kredi kartı ekle ama kullanma). Sahne anında kota dolarsa anlık upgrade.

### 13.3. Kaynak Tüketimi Uyarı Sistemi

**Rate limit yok**, ancak yüksek tüketim durumlarında uyarı verilecek:

```python
# backend/app/llm/usage_tracker.py

class UsageTracker:
    """LLM çağrılarını sayar, eşik aşılırsa uyarı yayar."""

    THRESHOLDS = {
        "gemini_rpm": 12,           # 15 RPM'in %80'i
        "gemini_daily_requests": 1200,  # 1500 RPD'nin %80'i
        "groq_rpm": 25,             # 30 RPM'in %80'i
    }

    def record(self, service: str, tokens: int):
        # ... tüketimi kaydet
        if self._exceeds_threshold(service):
            self._alert(service)

    def _alert(self, service: str):
        # 1. Backend log'a WARN yaz
        # 2. WebSocket ile frontend'e admin uyarısı gönder
        # 3. .env'deki ADMIN_WEBHOOK varsa Discord/Slack'e mesaj at
        ...
```

**Frontend'de admin paneli (basit):**
- Sayfanın altına küçük bir "🟢 Sistem Sağlıklı" rozeti
- Eşik aşılırsa "🟡 Yüksek tüketim" veya "🔴 Kota dolmak üzere" olur
- Demo öncesi göz at, demo başında yeşil olduğundan emin ol

### 13.4. Token Tasarrufu Stratejileri

| Strateji | Tasarruf |
|---|---|
| Aynı repo'yu cache'den dön | %100 (yeni LLM çağrısı yok) |
| Tarihçi: akıllı commit özetleme (Bölüm 8.3) | ~%70 büyük repolarda |
| Dedektif: önce static analysis, sadece bulguları LLM'e | ~%80 |
| Plan Agent: sadece metadata yolla, kod yolla**ma** | ~%90 |
| Mimar: sadece import grafı + klasör yapısı, kod gövdesi yok | ~%85 |

---

## 14. Kurulum ve Çalıştırma

### 14.1. Gereksinimler

- Node.js 20+
- Python 3.11+
- Docker + Docker Compose
- API keys: `GEMINI_API_KEY`, `GROQ_API_KEY`

### 14.2. Lokal Geliştirme

```bash
# 1. Repo klonla
git clone <repo>
cd repoarkeolog

# 2. Altyapı (postgres, redis, qdrant)
cd infra
docker-compose up -d

# 3. Backend
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# Başka terminalde:
celery -A app.tasks.celery_app worker --loglevel=info

# 4. Frontend
cd ../frontend
npm install
npm run dev  # http://localhost:3000
```

### 14.3. .env Şablonu

```bash
# backend/.env
DATABASE_URL=postgresql://user:pass@localhost:5432/repoarkeolog
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
GEMINI_API_KEY=...
GROQ_API_KEY=...

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 14.4. Production Deploy

| Bileşen | Platform | Komut |
|---|---|---|
| Frontend | Vercel | `vercel --prod` |
| Backend API | Railway | git push (auto-deploy) |
| Worker | Railway (ayrı service) | `celery -A app.tasks.celery_app worker` |
| Postgres | Railway plugin | otomatik |
| Redis | Railway plugin | otomatik |
| Qdrant | **Qdrant Cloud free tier** (önerilen, kolay) **veya** Railway custom Docker | Cloud için: panel'den hesap aç + `QDRANT_URL` env'e ekle |

---

## Ek: Hızlı Kontrol Listesi

Geliştirici bu dokümanı okuduktan sonra şu sorulara cevap verebilmeli:

- [ ] Neyi inşa ediyoruz, neden?
- [ ] Hangi 4 ajan var, ne yapıyorlar?
- [ ] Bir analizin uçtan uca akışını anlatabiliyor muyum?
- [ ] Frontend'de hangi sayfalar/sekmeler var?
- [ ] Kendi modülümün API sözleşmesi nedir?
- [ ] Şartname için hangi dosyaları repoda tutmalıyım?
- [ ] MVP nedir, Stretch nedir, neyi feda edebilirim?
- [ ] Demo akışında benim modülüm hangi anda öne çıkıyor?
- [ ] Hangi risk benim modülümü etkiler, planım ne?

Hepsi "evet" ise, kodlamaya başla.

---

**Versiyon:** 1.1
**Son Güncelleme:** Hackathon hazırlık aşaması

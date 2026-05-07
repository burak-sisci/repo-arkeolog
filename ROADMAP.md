# RepoArkeolog — ROADMAP

> Bu dosya Plan Agent tarafından otomatik güncellenir. Manuel değişiklik yapılmamalıdır.

## MVP (Hackathon Demo)

### Tamamlanan
- [ ] Altyapı: Docker Compose (PostgreSQL, Redis, Qdrant)
- [ ] Backend: FastAPI + Celery worker
- [ ] Pipeline: git clone + tree-sitter AST + Gemini embedding + Qdrant
- [ ] Plan Agent (Gemini 2.5 Flash)
- [ ] Mimar Ajan (Gemini) — mimari harita
- [ ] Tarihçi Ajan (Groq Llama) — git timeline
- [ ] Dedektif Ajan (Gemini) — sağlık raporu
- [ ] Onboarding Ajan (Gemini) — yol haritası
- [ ] Frontend: Landing page + Analiz sayfası
- [ ] Frontend: ProgressBar (WebSocket)
- [ ] Frontend: Özet sekmesi
- [ ] Frontend: Mimap sekmesi (Cytoscape)
- [ ] Frontend: Timeline sekmesi (vis-timeline)
- [ ] Frontend: Chat sekmesi (RAG)

## Stretch Goals
- [ ] Chat: Re-ranking ile daha iyi kaynak seçimi
- [ ] Mimar: Circular dependency tespiti
- [ ] Dedektif: Güvenlik açığı tespiti (Bandit, semgrep)
- [ ] Auth / kullanıcı sistemi
- [ ] Analiz geçmişi
- [ ] Birden fazla repo karşılaştırma

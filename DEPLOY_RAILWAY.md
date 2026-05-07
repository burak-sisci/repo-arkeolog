# Railway Deploy Rehberi

Tek Railway projesinde **5 servis**: Postgres, Redis, Backend (FastAPI), Worker (Celery), Frontend (Next.js).

---

## 1. Hesap & Proje

1. https://railway.app → "Login with GitHub".
2. Sağ üstten **New Project** → **Deploy from GitHub repo** → `burak-sisci/repo-arkeolog` seç.
3. Railway varsayılan olarak repoyu tarar; ilk taraması bizim için yeterli değil — manuel servis ekleyeceğiz.

---

## 2. Postgres ve Redis Add-on'ları

Aynı proje içinden:

1. **+ New** → **Database** → **Add PostgreSQL** → otomatik kurulur. `${{Postgres.DATABASE_URL}}` referansı oluşur.
2. **+ New** → **Database** → **Add Redis** → `${{Redis.REDIS_URL}}` referansı oluşur.

---

## 3. Backend Servisi (FastAPI)

1. **+ New** → **GitHub Repo** → `burak-sisci/repo-arkeolog`.
2. Servis adını `backend` yap.
3. **Settings → Source**:
   - **Root Directory:** `backend`
   - **Build Method:** `Dockerfile` (otomatik bulur).
4. **Settings → Deploy**:
   - **Start Command:** `./start-web.sh`  *(Dockerfile zaten bunu CMD yapıyor; gerekmez ama explicit olsun)*
5. **Settings → Networking**:
   - **Generate Domain** bas → `https://backend-xxx.up.railway.app` benzeri URL alacaksın.
6. **Variables** (Variables sekmesi):
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   CEREBRAS_API_KEY=<senin Cerebras key>
   CORS_ORIGINS=https://frontend-xxx.up.railway.app
   QDRANT_URL=
   GEMINI_API_KEY=
   GROQ_API_KEY=
   ```
   > `CORS_ORIGINS` değerini Frontend domain'ini aldıktan sonra güncelle.

---

## 4. Worker Servisi (Celery)

Aynı imajı kullanan ikinci bir servis ekliyoruz.

1. **+ New** → **GitHub Repo** → tekrar aynı repo.
2. Servis adı `worker`.
3. **Settings → Source**:
   - **Root Directory:** `backend`
   - **Build Method:** `Dockerfile`
4. **Settings → Deploy**:
   - **Start Command:** `./start-worker.sh` *(bunu **mutlaka** override et — yoksa ikinci uvicorn ayağa kalkar)*
   - **Health Check:** kapat (worker'ın HTTP endpoint'i yok).
5. **Settings → Networking**: **Generate Domain bağlama** — worker public olmasın.
6. **Variables**: backend'le aynı set.
   - Pratik yöntem: backend'in variable'larını **"Shared Variables"** olarak işaretle, worker bunları otomatik alır.

---

## 5. Frontend Servisi (Next.js)

1. **+ New** → **GitHub Repo** → tekrar aynı repo.
2. Servis adı `frontend`.
3. **Settings → Source**:
   - **Root Directory:** `frontend`
   - **Build Method:** `Dockerfile`
4. **Settings → Build**:
   - **Build Args** (Dockerfile ARG'larıyla aynı isim):
     ```
     NEXT_PUBLIC_API_URL=https://backend-xxx.up.railway.app
     NEXT_PUBLIC_WS_URL=wss://backend-xxx.up.railway.app
     ```
   > Bu değişkenler **build time**'da bundle'a yazılır.
5. **Settings → Networking**: **Generate Domain**.
6. **Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://backend-xxx.up.railway.app
   NEXT_PUBLIC_WS_URL=wss://backend-xxx.up.railway.app
   ```
7. Frontend domain'ini öğrenince **backend servisinin** `CORS_ORIGINS` değişkenini güncelle ve backend'i redeploy et.

---

## 6. Migration

Backend container ilk kalkışında `start-web.sh` içindeki `alembic upgrade head` Postgres tablolarını kurar. Manuel tetiklemek isterseniz Railway dashboard'da backend servisi → **Deploy** sekmesi → **Restart**.

---

## 7. Kontrol Listesi (Yayına Almadan Önce)

- [ ] Backend `https://...up.railway.app/api/health` → `{"status":"ok"}`
- [ ] Frontend açılıyor, dark mode çalışıyor
- [ ] `POST /api/analyze` 202 dönüyor
- [ ] WebSocket `/ws/progress/<id>` bağlanıyor (Network tab → "WS")
- [ ] Worker logları "celery@... ready" gösteriyor
- [ ] Cerebras `qwen-3-235b` çağrısı 200 dönüyor (Worker log)
- [ ] CORS hatası yok (Browser console)

---

## 8. Maliyet

Railway tipik kullanımda **$5–20/ay** (proje bazlı). Postgres + Redis kapasiteleri arttıkça yükselir. Cerebras ayrı.

---

## 9. Sorun Giderme

| Belirti | Kontrol |
|---------|---------|
| Backend 502 | Worker logu → `psycopg2` veya `alembic` hatası mı? |
| WebSocket 404 | `wss://` (https üzerinde) kullanılıyor mu? `NEXT_PUBLIC_WS_URL` doğru mu? |
| CORS error | Frontend domain'i `CORS_ORIGINS`'te ekli mi? backend redeploy oldu mu? |
| Worker görev almıyor | Backend ve Worker aynı `REDIS_URL`'i mi kullanıyor? |
| Build hatası: tree-sitter-* | Dockerfile cache temizle: Settings → Redeploy → "Clear build cache" |
| Gemini 429 | Gemini key boş bırakılırsa embedding atlanır, problem değil |

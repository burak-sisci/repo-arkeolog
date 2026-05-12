# Katkı Rehberi — RepoArkeolog (SolveX 2026)

Bu doküman, **SolveX AI Hackathon 2026 Teknik Şartnamesi**'ndeki versiyon kontrol ve AI-augmented development standartlarını projeye nasıl uyguladığımızı tanımlar. Tüm takım üyeleri ve dış katkıcılar bu kurallara uymalıdır.

---

## 1. Takım

| Rol | Üye | GitHub | Sorumluluk |
|-----|-----|--------|-----------|
| **Lead Developer / Maintainer** | burak-sisci | [@burak-sisci](https://github.com/burak-sisci) | Repo yönetimi, PR onayı, kod standartları |
| **Feature Developer** | eminehatundincer | [@eminehatundincer](https://github.com/eminehatundincer) | Issue → feature/fix branch → PR |
| **Feature Developer** | Serifenurr | [@Serifenurr](https://github.com/Serifenurr) | Issue → feature/fix branch → PR |

---

## 2. Versiyon Kontrol Disiplini *(GitHub Flow)*

### 2.1. `main` Dalı
- `main` **dağıtıma hazır** sürümü temsil eder.
- **`main`'e doğrudan push YASAK.**
- Tüm değişiklikler PR üzerinden gelir. Lead Maintainer onayı zorunludur.

### 2.2. Branch İsimlendirme
| Tür | Format | Örnek |
|-----|--------|-------|
| Yeni özellik | `feature/<kısa-ad>` | `feature/dark-theme-toggle` |
| Hata düzeltme | `fix/<kısa-ad>` | `fix/cytoscape-null-deref` |
| Doküman | `docs/<kısa-ad>` | `docs/readme-deploy` |
| Refactor | `refactor/<kısa-ad>` | `refactor/agent-base` |
| Yapılandırma | `chore/<kısa-ad>` | `chore/bump-deps` |

### 2.3. Commit Mesajları *(Conventional Commits)*
Şimdiki zaman, kısa ve teknik:

```
<tür>: <şimdiki zamanda kısa özet>
```

**Tür**ler: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`.

✅ İyi:
- `feat: kullanıcı kimlik doğrulama katmanı eklendi`
- `fix: branch fallback sırasında hatalı klasör temizliği düzeltildi`
- `refactor: chunker dil yöneticisi sadeleştirildi`

❌ Kötü:
- `son hali`
- `update`
- `büyük değişiklik`

### 2.4. Pull Request
1. Bir Issue ile başla.
2. `feature/...` ya da `fix/...` branch'i aç.
3. PR şablonunu eksiksiz doldur. **AI Traceability bölümü zorunlu.**
4. CI yeşil olmalı.
5. **En az 1 takım üyesinin Code Review onayı** gerekir (şartname §4).
6. Squash merge tercih edilir; yorum kirliliği azalır.
7. Branch merge sonrası silinir.

### 2.5. Çakışma (Conflict)
Çakışma olursa **rebase** edip yerel olarak çöz:

```bash
git fetch origin
git rebase origin/main
# çakışmaları çöz, git add ., git rebase --continue
git push --force-with-lease
```

Kuralı bilmiyorsan `--force` yerine `--force-with-lease` kullan: yanlışlıkla başkasının commit'ini silmez.

---

## 3. AI-Augmented Development *(şartname §5)*

Proje, **Cerebras Inference** üzerinden çalışan iki AI yapısını simüle eder. Çalışma zamanında tüm beş ürün ajanı (Plan, Mimar, Tarihçi, Dedektif, Onboarding) `qwen-3-235b-a22b-instruct-2507` modeli üzerinde çalışır.

### 3.1. Plan Agent
- Geliştirme öncesi mimari plan ve alt görevleri çıkarır.
- Çıktısı [`ARCHITECTURE.md`](ARCHITECTURE.md) ve [`ROADMAP.md`](ROADMAP.md) dosyalarında saklanır.
- Issue'lar Plan Agent'ın belirlediği alt görevlerden türetilir.

### 3.2. Skills Agent
- Karmaşık algoritma, güvenlik veya performans gerektiren noktalarda **Uzman Yazılımcı** rolünde devreye girer.
- Etkileşim çıktıları:
  - PR açıklamasında **AI Traceability** bölümünde,
  - Veya kod yorumlarında `# AI:` / `// AI:` etiketleriyle belirtilir.

### 3.3. AI Traceability İşaretleme

Kod dosyalarının başında veya kritik fonksiyonların üzerinde şu formatı kullan:

```python
# AI: Skills Agent (Cerebras qwen-3-235b) ile JSON parse heuristikleri
# yeniden yazıldı. Refactor: 2026-05-07.
```

```typescript
// AI: Plan Agent ile rol sınıflandırma sözlüğü çıkarıldı.
// Skills Agent: cytoscape unmount race condition için iteratif Tarjan SCC.
```

Detaylı kayıt için: [`AI_USAGE.md`](AI_USAGE.md).

### 3.4. Final Review
Proje tesliminden önce kodun tamamı Cerebras qwen-3-235b ile **Refactoring + Optimization** taramasından geçirilir. Bulgular bir özet PR'da raporlanır.

---

## 4. Iş Takibi *(şartname §6)*

- Her görev → **GitHub Issue**.
- Her Issue **bir geliştiriciye** atanır.
- PR'da `Closes #<issue>` ile bağla.
- Etiketler: `enhancement`, `bug`, `documentation`, `ai-assisted`, `refactor`.

---

## 5. Yerel Geliştirme Kurulumu

[README.md → Hızlı Başlangıç](README.md#hızlı-başlangıç) bölümüne bak. Windows kullanıcıları için Celery'yi `--pool=solo` flag'i ile başlatmak şarttır.

---

## 6. Yardım

- Süreç sorusu: Lead Maintainer'a yaz.
- Teknik takılma: Issue aç ve `question` etiketi koy.

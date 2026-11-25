# Warehouse Management System (WMS) / Ombor Boshqaruv Tizimi

Zamonaviy elektron tijorat va logistika markazlari uchun to'liq funksional Ombor Boshqaruv Tizimi (WMS). Tizim **FBW** (*Fulfillment by Warehouse*) va **FBS** (*Fulfillment by Seller*) operatsion modellarini qo'llab-quvvatlaydi, tovarlarning kirimidan tortib, saqlash, yig'ish, jo'natish va qaytarishgacha bo'lgan barcha ombor jarayonlarini avtomatlashtiradi.

---

## 🚀 Texnologiyalar steki (Tech Stack)

- **Backend Freymvork:** Python 3.12, Django 5.2
- **Ma'lumotlar bazasi:** PostgreSQL 16
- **WSGI / Web Server:** Gunicorn 22.0, Nginx (Alpine) yuk taqsimlovchi (Load Balancer & Reverse Proxy)
- **Frontend & UI:** Django Templates, Tailwind CSS, Django Crispy Forms (Crispy Tailwind)
- **Statik fayllar:** WhiteNoise
- **Konteynerlashtirish:** Docker, Docker Compose
- **CI/CD:** GitHub Actions (Lint, Test, SSH Auto-Deployment)
- **Formatlash & Linter:** Flake8

---

## ✨ Asosiy Funksionallik (Features)

1. **Rollar bo'yicha ko'p bosqichli kirish huquqlari (RBAC):**
   - **Admin:** Tizim sozlamalari, audit, to'liq boshqaruv.
   - **Ombor Menejeri (Warehouse Manager):** Ombor holati, joylashuvlar, hisobotlar.
   - **Qabul Operatori (Receiver):** Kirim jo'natmalarini tekshirish, qabul qilish, barkodlarni tasdiqlash.
   - **Yig'uvchi (Picker):** Buyurtmalar bo'yicha yig'ish (Pick list), tovarlarni joyidan olish.
   - **Dispetcher (Dispatcher):** Qadoqlash, posilkalarni shakllantirish, jo'natish.
   - **Qaytarish Operatori (Returns Operator):** Mijozlardan qaytgan tovarlar ekspertizasi va qaror qabul qilish (restock / dispose / quarantine).
   - **Sotuvchi (Seller):** O'z tovarlari katalogi, qoldiqlar va buyurtmalar nazorati.

2. **Katalog va Mahsulotlar (Catalog & SKU):**
   - Ko'p bosqichli kategoriyalar, SKU, EAN/UPC Shtrix-kodlar.
   - O'lchamlar, vazn, hajm, brend va yaroqlilik muddati (perishable) nazorati.
   - Minimal zaxira limiti bo'yicha ogohlantirishlar.

3. **Ombor va Topologiya (Warehouse & Inventory):**
   - Ko'p zonali ierarxik saqlash: Ombor -> Zona -> Qator (Aisle) -> Stellaj (Rack) -> Tokcha (Shelf) -> O'rin (Position).
   - Partiyalar (Batches) bo'yicha hisob: FIFO/FEFO tamoyillari, muddat monitoringi.
   - Idempotent zaxira harakatlari (Stock Movements).

4. **Logistika (Logistics):**
   - **Inbound:** Yetkazib beruvchilar hisobi, kirim hujjatlari, joylashtirish (putaway).
   - **Outbound:** Buyurtmalarni avtomatik zaxiradan band qilish (Allocation), yig'ish, qadoqlash (Packages) va jo'natish.
   - **Returns:** Reverse logistics va mahsulot holatini baholash.

5. **Monitoring va Audit:**
   - Real vaqt rejimidagi boshqaruv paneli (Dashboard) statistikasi.
   - Barcha harakatlar bo'yicha batafsil audit jurnali (`AuditLog`).
   - Salomatlik tekshiruvi API (`/health/`).

---

## 🐳 Docker yordamida tezkor ishga tushirish (Quick Start)

Loyihani Docker va Docker Compose orqali bitta buyruq bilan ishga tushirishingiz mumkin.

### 1. Muhit o'zgaruvchilarini sozlash
Loyihaning ildiz papkasida `.env` faylini yarating yoki namunadan nusxa oling:
```bash
cp .env.example .env
```
Kerak bo'lsa, `.env` faylidagi maxfiy kalit va parol parametrlarini o'zgartiring.

### 2. Konteynerlarni yig'ish va ishga tushirish
```bash
docker compose up -d --build
```

Bu quyidagi servislarni ishga tushiradi:
- `db`: PostgreSQL 16 ma'lumotlar bazasi
- `migrate`: Migratsiyalar va statik fayllarni yig'ish (bir martalik servis)
- `web1` & `web2`: 2 ta Gunicorn replikasi
- `nginx`: 80-portda teskari proksi va statik fayllarni tarqatuvchi server

### 3. Demo ma'lumotlarni yuklash (Seeding)
Konteyner ichida demo foydalanuvchilar, mahsulotlar va boshlang'ich zaxirani yaratish:
```bash
docker compose exec web1 python manage.py seed_data
```

### 4. Tizimga kirish
Brauzeringizda oching:
```
http://localhost/
```

---

## 💻 Mahalliy muhitda ishga tushirish (Local Development)

### 1. Virtual muhitni yaratish va faollashtirish
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash
`.env` faylida PostgreSQL yoki test uchun SQLite parametrlarini sozlang.

### 4. Migratsiyalarni amalga oshirish va ma'lumotlarni to'ldirish
```bash
python manage.py migrate
python manage.py seed_data
```

### 5. Serverni ishga tushirish
```bash
python manage.py runserver
```

---

## 🔑 Foydalanuvchilar va kirish

Tizimda rollar: Admin, Ombor menejeri, Qabul operatori, Yig'uvchi, Dispetcher, Qaytarish operatori, Sotuvchi.

- **Lokal muhit:** `python manage.py seed_data` demo foydalanuvchilarni yaratadi (parollar `seed_data` buyrug'ida, faqat lokal sinov uchun).
- **AWS (production):** demo foydalanuvchilar yaratilmaydi. Admin paroli CloudFormation tomonidan **AWS Secrets Manager**'da avtomatik generatsiya qilinadi (`brightflame/admin` secret) — kodda ham, GitHub'da ham parol yo'q.

---

## 🌐 Asosiy URL Manzillar (Main Routes)

- `/` — Boshqaruv paneli (Dashboard)
- `/login/` / `/logout/` — Tizimga kirish va chiqish
- `/catalog/` — Mahsulotlar va kategoriyalar katalogi
- `/warehouse/` — Omborlar, saqlash joylari, partiyalar va zaxira harakatlari
- `/logistics/` — Kirim jo'natmalari, chiqim buyurtmalari, yig'ish, qadoqlash va qaytuvlar
- `/accounts/` — Foydalanuvchilar va sotuvchilar profillari
- `/admin/` — Django boshqaruv paneli (Django Admin)
- `/health/` — Tizim salomatligi tekshiruvi (Health Check API: JSON `{"status": "ok"}`)

---

## ☁️ AWS bulut arxitekturasi

```
Foydalanuvchi → Internet → brightflame.uz (DNS)
        → Application Load Balancer (80/443)
        → Auto Scaling Group: EC2 t3.micro × 1–3 (Docker + Gunicorn)
              ├→ Amazon RDS PostgreSQL 16 (private subnet)
              ├→ Amazon S3 (mahsulot rasmlari, private bucket)
              ├→ AWS Secrets Manager (DB paroli, SECRET_KEY, admin paroli)
              └→ Amazon CloudWatch (loglar, metrikalar, alarmlar, dashboard)
Xavfsizlik: Security Groups + IAM (minimal huquqlar), SSH yopiq (SSM Session Manager)
```

Butun infratuzilma bitta CloudFormation shabloni: [`infra/aws/brightflame.yml`](infra/aws/brightflame.yml).

| Qism | Xizmat | Izoh |
|---|---|---|
| Compute | EC2 + Auto Scaling | O'rtacha CPU 50% dan oshsa instance qo'shiladi (max 3), tushsa kamayadi |
| Load balancing | Application Load Balancer | `/health/` (DB tekshiruvi bilan) orqali sog'lom instance'larga taqsimlaydi |
| Database | RDS PostgreSQL db.t4g.micro | Internetga yopiq, faqat ilova SG'dan 5432 |
| Storage | S3 | `Product.image` — django-storages, presigned URL |
| Security | Security Groups, IAM, Secrets Manager | ALB: 80/443 · EC2: faqat ALB'dan 8000 · RDS: faqat EC2'dan 5432 |
| Monitoring | CloudWatch | Docker loglari, dashboard, alarmlar (unhealthy host, 5xx, RDS CPU) |

**Ochiq portlar:** 80 (HTTP → HTTPS'ga yo'naltiriladi), 443 (HTTPS) — faqat ALB'da. SSH (22) umuman ochilmagan: serverga kirish AWS Systems Manager Session Manager orqali (IAM bilan nazorat qilinadi). PostgreSQL (5432) faqat ilova serverlari uchun.

### Ishga tushirish
1. AWS Console → CloudFormation → *Create stack* → `infra/aws/brightflame.yml`, stack nomi `brightflame`.
2. Outputs'dagi `GitHubDeployRoleArn`ni GitHub repo → Settings → Variables → `AWS_DEPLOY_ROLE_ARN` ga yozing.
3. Domen: DNS'da `www` CNAME → `LoadBalancerDNS`. HTTPS uchun ACM sertifikat ARN'ini `CertificateArn` parametriga bering.
4. Himoyadan keyin: S3 bucket'ni bo'shatib, stack'ni o'chiring — barcha resurslar o'chadi.

## 🔄 CI/CD (GitHub Actions)

`.github/workflows/ci.yml`:
1. **test** — PostgreSQL servisi bilan migratsiyalar, Flake8 va testlar.
2. **docker-build** — production image yig'ilishini tekshiradi.
3. **deploy** (`main` ga push) — GitHub **OIDC** orqali AWS'ga kiradi (access key yo'q), Auto Scaling Group'da *instance refresh* boshlaydi: yangi instance ko'tarilib sog'lom bo'lgach eskisi o'chiriladi — uzilishsiz deploy.

Lokal Docker Compose'da ham load balancing bor: nginx (`least_conn`, failover) → `web1`, `web2`.

---

## 🔌 API Adapterlar va Tashqi Tizimlar Integratsiyasi (API Adapter Note)

Ushbu WMS arxitekturasi tashqi marketpleyslar va elektron tijorat tizimlari (Wildberries, Uzum Market, Ozon, Shopify va h.k.) bilan integratsiya qilinishi uchun modulli arxitekturada loyihalashtirilgan.

- **Katalog sinxronizatsiyasi:** `apps/catalog` modellari tashqi platformalarning maqolalari (masalan, `wb_article`, `nm_id`) va barkodlari bilan to'liq mos keladi.
- **Zaxiralarni sinxronlash:** Ombor qoldiqlari o'zgarganda webhooks yoki davriy sinxronizatorlar orqali tashqi bozorlarga qoldiqlar yuborilishi mumkin.
- **Buyurtmalarni qabul qilish:** Tashqi platformalardan tushgan buyurtmalar WMS tizimida avtomatik ravishda `OutboundOrder` formatida yaratiladi hamda tegishli yig'uvchi va omborga biriktiriladi.

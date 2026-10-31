# Mehmonxona Telegram Boti (`bot/`)

Ushbu loyiha mehmonxona tizimining Telegram boti boʻlib, u toʻliq **veb-sayt REST API mijozi (client)** sifatida ishlaydi. Botning oʻziga tegishli bronlar bazasi mavjud **emas**; barcha bronlar, xonalar maʼlumotlari va biznes qoidalari faqat veb-sayt APIʼsida saqlanadi va boshqariladi.

Botda qilingan bron veb-saytda qilingan bron bilan bir xil hisoblanadi va ikkala platformada ham birdek koʻrinadi.

---

## Asosiy imkoniyatlar
- 📅 **Xonalarni bron qilish**: Xonani tanlash, kirish sanasi («Bugun», «Ertaga» yoki klaviaturadan kiritish), kechalar soni (1–30), ism va telefon raqami (kontaktni ulashish yoki yozish).
- 🛏 **Xonalar katalogi**: Har bir xona uchun fotosurat (cover_960), narx, qulayliklar va tavsif. Rasmlar galereyasi (media group) va zaxira yuklash (fallback) mexanizmi.
- 💳 **Toʻlov va chek qabul qilish**: Karta maʼlumotlari va bron kodi bilan qatʼiy shablon boʻyicha toʻlov xabari. Toʻlov cheklarini (JPG, PNG, PDF 5 MB gacha) qabul qilish va APIʼga yuklash. Bot qayta ishga tushganda ham chekni soʻnggi faol bronga avtomatik biriktirish.
- 📋 **Mening bronlarim**: Telegram orqali qilingan bronlar va tasdiqlangan telefon raqami (`data/users.json`) orqali saytdagi barcha bronlarni koʻrish.
- 🔎 **Bronni kod bilan topish**: Kod va telefon raqami orqali bron holatini tekshirish.
- 📍 **Manzil va aloqa**: Mehmonxona manzili, telefon raqami, ish vaqti va xaritadagi manzili.
- 👑 **Administrator boshqaruvi**:
  - Sayt tomonidan adminga yuborilgan toʻlov cheki ostidagi «✅ Tasdiqlash» (`ok:<id>`) va «❌ Rad etish» (`no:<id>`) tugmalarini qayta ishlash.
  - `/bronlar` buyrugʻi orqali yaqinlashib kelayotgan tasdiqlangan bronlarni koʻrish.
- 🔗 **Deep link qoʻllab-quvvatlash**:
  - `/start room_<key>`: Koʻrsatilgan xona uchun sana tanlash bosqichini ochish.
  - `/start b_<key>_<YYYYMMDD>_<nights>`: Xona boʻshligini tekshirib, toʻgʻridan-toʻgʻri ism kiritish bosqichiga oʻtish.

---

## Oʻrnatish va ishga tushirish

### 1. Telegram bot yaratish (@BotFather)
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrugʻini yuboring.
3. Botingiz uchun nom va foydalanuvchi nomini (oxiri `bot` bilan tugaydigan, masalan: `silkroad_hotel_bot`) kiriting.
4. BotFather bergan **HTTP API token**ni nusxalab oling.

### 2. Admin Telegram ID raqamini aniqlash
1. Telegramda [@userinfobot](https://t.me/userinfobot) botiga kiring yoki `/start` bosing.
2. Bot sizning raqamli `Id` raqamingizni qaytaradi (masalan: `123456789`).
3. Bir nechta admin boʻlsa, ID raqamlarini vergul bilan ajratib yozing (`123456789,987654321`).

### 3. `.env` faylini sozlash
Loyihaning `bot/` jildida `.env.example` faylidan nusxa olib, `.env` faylini yarating:

```bash
cp .env.example .env
```

`.env` tarkibi:
```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321
API_BASE_URL=http://localhost:8000
API_KEY=hotel_secret_api_key_123
```

> [!IMPORTANT]
> `BOT_TOKEN`, `ADMIN_IDS` va `API_KEY` qiymatlari mehmonxona veb-saytining (`website/`) `.env` faylidagi qiymatlar bilan **mutlaqo bir xil** boʻlishi shart!

### 4. Mahalliy muhitda ishga tushirish
Python 3.11+ talab qilinadi.

```bash
# Virtual muhit yaratish va faollashtirish
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Bogʻliqliklarni oʻrnatish
pip install -r requirements.txt

# Botni ishga tushirish
python bot.py
```

---

## 24/7 Rejimda ishga tushirish

### A. Systemd xizmati sifatida (Linux server)
`/etc/systemd/system/hotelbot.service` faylini yarating:

```ini
[Unit]
Description=Hotel Booking Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/hotel/bot
ExecStart=/var/www/hotel/bot/venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=/var/www/hotel/bot/.env

[Install]
WantedBy=multi-user.target
```

Xizmatni faollashtiring va ishga tushiring:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hotelbot
sudo systemctl start hotelbot
sudo systemctl status hotelbot
```

Jurnallarni koʻrish:
```bash
journalctl -u hotelbot -f
```

---

### B. Docker yordamida ishga tushirish
Docker orqali ishlatish uchun `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

Qurish va yurgizish:
```bash
docker build -t hotel-booking-bot .
docker run -d --name hotel-bot --restart always --env-file .env hotel-booking-bot
```

---

## Yangilash tartibi (How to update)
Botni serverda yangilash uchun quyidagi qadamlarni bajaring:

```bash
# 1. Loyiha jildiga oʻting
cd /var/www/hotel/bot

# 2. Yangi kodni oling
git pull origin main

# 3. Virtual muhitda yangi kutubxonalarni oʻrnating
source venv/bin/activate
pip install -r requirements.txt

# 4. Xizmatni qayta ishga tushiring
sudo systemctl restart hotelbot

# 5. Jurnallarni tekshiring
journalctl -u hotelbot -n 50 --no-pager
```

---

## Testlarni ishga tushirish

Loyiha toʻliq testlar bilan qamrab olingan:
```bash
pytest bot/tests -v
```
Barcha 62 ta test tarmoqqa bogʻlanmasdan, respx va mocklar yordamida tezkor ishlaydi va API shartnomasiga mosligini toʻliq tekshiradi.

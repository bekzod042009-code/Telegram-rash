# Rash yordamchi

Telegram mini ilova: o‘qituvchi test yaratadi, o‘quvchi kod yoki fan bo‘yicha topib yechadi.
Python (FastAPI + aiogram) + PostgreSQL, Railway uchun tayyor.

## Qo‘lda qilinadigan ishlar

1. **Bot yarating.** Telegramda @BotFather → `/newbot` → tokenni nusxalang.
2. **Railway.** railway.com → New Project → *Deploy from GitHub repo* → `telegram-rash`.
3. **Baza.** Shu loyihada: *+ New* → *Database* → *PostgreSQL*.
4. **O‘zgaruvchilar.** Ilova servisi → *Variables*:

   | Nomi | Qiymati |
   |---|---|
   | `BOT_TOKEN` | BotFather bergan token |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `ADMIN_IDS` | sizning Telegram ID (7-qadamda olinadi) |
   | `PAYMENT_INFO` | ixtiyoriy: to‘lov uchun karta yoki admin username |

5. **Domen.** Servis → *Settings* → *Networking* → *Generate Domain*.
6. **Qayta deploy** qiling (*Deployments* → *Redeploy*).
7. Botga `/id` yuboring, chiqqan raqamni `ADMIN_IDS` ga yozing (yana deploy bo‘ladi).
8. Botga `/start` yuboring → **Ilovani ochish**.

Menyu tugmasi va ilova manzili avtomatik sozlanadi. Tokenni hech qachon GitHub'ga yozmang.

Faqat bitta nusxa (replica) ishlasin: bot long polling orqali ishlaydi.

## To‘lovlar

Click/Payme hali ulanmagan. Balans to‘ldirish, kredit paketi va pul yechish **ariza** sifatida
adminga keladi: Admin → Daromad → Tasdiqlash / Rad etish. Pulni o‘zingiz tekshirasiz va o‘tkazasiz.

## Variantlar va tekshiruv

Oddiy testda har bir variant uchun matn qatori bor (rasmli savolda ixtiyoriy).
O‘qituvchi: Testlarim → Natijalar → o‘quvchi. Imlo xatosi sabab xato olingan yozma javobni
**To‘g‘ri deb hisoblash** mumkin (bekor qilish ham bor).

## Milliy sertifikat qoliplari

Test yaratishda **Test qolipi** tanlanadi (`app/templates.py`). Huquqshunoslik uchun spetsifikatsiya yo‘q.

* Xom ball: har savolga 1,3 / 2,2 / 3,2 (o‘qituvchi tanlaydi).
* Rash (`app/scoring.py`): dixotomik model, T = 50 + 10Z, 0–75. Kamida 10 o‘quvchi kerak;
  har birining birinchi urinishi olinadi.
* Yozma ish va esse qo‘lda baholanadi: Testlarim → Natijalar → o‘quvchi.
* Kimyo, biologiya, ona tili: yakuniy = (Rash + yozma 75 ballga keltirilgan) / 2.
  Rasmiy birlashtirish formulasi spetsifikatsiyada yo‘q.
* Chet tili: Listening, Reading, Writing, Speaking o‘rtachasi; Use of English alohida ko‘rsatiladi.
  Audio yuklash hozircha yo‘q.

Ballar taxminiy, rasmiy natija farq qilishi mumkin.

## Rasmlar

Faqat oddiy testda. JPG, PNG, WEBP; telefonda kichraytiriladi (1600 px gacha) va bazada saqlanadi.

## Tuzilma

    app/main.py        server
    app/bot.py         bot
    app/db.py          baza jadvallari
    app/checking.py    yozma javobni tekshirish
    app/routes/        API (o‘qituvchi, o‘quvchi, admin)
    web/               mini ilova (HTML, CSS, JS)

## Hozircha yo‘q

Click/Payme, Listening uchun audio.

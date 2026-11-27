import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
PAYMENT_INFO = os.getenv("PAYMENT_INFO", "").strip()
PORT = int(os.getenv("PORT", "8000"))

_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip() or (f"https://{_domain}" if _domain else "")

SUBJECTS = ["Ona tili", "Adabiyot", "Tarix", "Matematika", "Fizika", "Kimyo",
            "Biologiya", "Geografiya", "Ingliz tili", "Rus tili", "Informatika"]
LETTERS = "ABCDEF"

DEFAULT_SETTINGS = {
    "tc": 2,    # test yaratish narxi (kredit)
    "tw": 100,  # yangi o'qituvchiga sovg'a
    "sw": 50,   # yangi o'quvchiga sovg'a
    "ref": 20,  # do'st taklifi
    "com": 10,  # o'qituvchi ulushi (%)
    "pk": [{"c": 1000, "p": 400000}, {"c": 500, "p": 220000},
           {"c": 250, "p": 120000}, {"c": 100, "p": 50000}],
}

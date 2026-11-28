"""O'qituvchi: rasm yuklash, test yaratish, testlarim."""
import asyncio
import io
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from .. import auth, checking, config, db, scoring, templates
from .shared import TESTS_SQL, account, calibration, card

router = APIRouter()
MAX_UPLOAD = 6 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PENDING_IMAGES = 150


def prepare_image(raw: bytes) -> bytes:
    """Rasmni tekshiradi, kichraytiradi va JPEG qilib qayta saqlaydi."""
    with Image.open(io.BytesIO(raw), formats=["JPEG", "PNG", "WEBP"]) as src:
        if src.width * src.height > MAX_PIXELS:
            raise ValueError("too large")
        img = ImageOps.exif_transpose(src)
        img.thumbnail((1600, 1600))
        img = img.convert("RGBA")
        flat = Image.new("RGB", img.size, "white")
        flat.paste(img, mask=img.getchannel("A"))
        out = io.BytesIO()
        flat.save(out, "JPEG", quality=85, optimize=True)
        return out.getvalue()


@router.post("/api/images")
async def upload_image(request: Request, acc=Depends(auth.teacher)):
    raw = bytearray()
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "Rasm juda katta (6 MB gacha).")
    try:
        data = await asyncio.to_thread(prepare_image, bytes(raw))
    except Exception:
        raise HTTPException(400, "Rasm oʻqilmadi. JPG yoki PNG yuklang.")
    # Testga ulanmay qolgan eski rasmlar tozalanadi.
    await db.pool.execute(
        "DELETE FROM images WHERE test_code IS NULL AND created_at < now() - interval '1 day'")
    pending = await db.pool.fetchval(
        "SELECT COUNT(*) FROM images WHERE owner_id = $1 AND test_code IS NULL", acc["id"])
    if pending >= MAX_PENDING_IMAGES:
        raise HTTPException(400, "Juda koʻp rasm yuklandi. Testni saqlang yoki keyinroq urinib koʻring.")
    image_id = secrets.token_urlsafe(18)
    await db.pool.execute("INSERT INTO images(id, owner_id, data) VALUES ($1, $2, $3)", image_id, acc["id"], data)
    return {"id": image_id}


@router.delete("/api/images/{image_id}")
async def delete_image(image_id: str, acc=Depends(auth.teacher)):
    await db.pool.execute(
        "DELETE FROM images WHERE id = $1 AND owner_id = $2 AND test_code IS NULL", image_id, acc["id"])
    return {"ok": True}


class Question(BaseModel):
    t: str = Field(default="", max_length=8000)
    img: str | None = Field(default=None, max_length=64)
    w: bool = False
    a: str | None = Field(default=None, max_length=1)
    acc: list[str] = Field(default_factory=list, max_length=20)
    md: Literal["key", "exact", "fuzzy"] = "key"
    opts: list[str] = Field(default_factory=list, max_length=6)
    part: Literal["", "a", "b", "c", "d", "e", "f"] = ""


class NewTest(BaseModel):
    title: str = Field(default="", max_length=120)
    min: int = Field(ge=1, le=600)
    k: int = Field(ge=2, le=6)
    printed: bool = False
    pub: bool = False
    open: bool = True
    subj: str = ""
    pay: Literal["m", "c"] = "m"
    price: int = Field(default=0, ge=0, le=10_000_000)
    tpl: str = Field(default="", max_length=10)
    questions: list[Question] = Field(min_length=1, max_length=120)


def layout(body: NewTest) -> list[dict]:
    """Har bir yuborilgan qator qaysi savolga tegishli ekani. Qolipda tartib serverda tekshiriladi."""
    if not body.tpl:
        if len(body.questions) > 100:
            raise HTTPException(400, "Savollar soni 100 tadan oshmasin.")
        return [{"label": str(i), "type": "free", "sec": "", "k": body.k, "cont": False}
                for i in range(1, len(body.questions) + 1)]
    tpl = templates.TEMPLATES.get(body.tpl)
    if not tpl:
        raise HTTPException(400, "Bunday qolip yoʻq.")
    wrong = HTTPException(400, "Savollar tanlangan qolipga mos emas.")
    out, pos = [], 0
    for slot in tpl["slots"]:
        if pos >= len(body.questions):
            raise wrong
        parts = [""]
        if slot["type"] == "o" and body.questions[pos].part == "a":
            # Ochiq savolda a, b, ... bandlar ketma-ket keladi.
            parts = []
            for letter in "abcdef":
                if pos + len(parts) >= len(body.questions) or body.questions[pos + len(parts)].part != letter:
                    break
                parts.append(letter)
        for part in parts:
            if body.questions[pos].part != part:
                raise wrong
            out.append({"label": f"{slot['n']}{part}", "type": slot["type"], "sec": slot["sec"],
                        "k": slot["k"], "cont": part not in ("", "a"), "max": slot.get("max", 0)})
            pos += 1
    if pos != len(body.questions):
        raise wrong
    return out


def build_key(body: NewTest) -> list[dict]:
    key = []
    for q, meta in zip(body.questions, layout(body)):
        name, kind, k = meta["label"], meta["type"], meta["k"]
        written = q.w if kind == "free" else kind in ("o", "m")
        # Keyingi bandlar matni a band bilan birga beriladi.
        text = "" if body.printed else q.t.strip()
        img = None if body.printed else q.img
        if not body.printed and not meta["cont"] and not text and not img:
            raise HTTPException(400, f"{name}-savolda matn yoki rasm yoʻq.")
        accepted, options, answer, most = [], [], None, 0
        if kind == "m":
            most = meta["max"]
        elif written:
            accepted = [a.strip() for a in q.acc if checking.norm(a)]
            if not accepted or any(len(a) > 200 for a in accepted):
                raise HTTPException(400, f"{name}-savolda yozma javob notoʻgʻri.")
        else:
            if not q.a or q.a not in config.LETTERS[:k]:
                raise HTTPException(400, f"{name}-savolda javob belgilanmagan.")
            answer = q.a
            if not body.printed:
                options = [o.strip() for o in q.opts[:k]]
                options += [""] * (k - len(options))
                if any(len(o) > 500 for o in options):
                    raise HTTPException(400, f"{name}-savolda variant matni juda uzun.")
                # Rasmli savolda variantlar rasmning ichida bo'lishi mumkin.
                if not img and not all(options):
                    raise HTTPException(400, f"{name}-savolda variant matni yoʻq.")
        key.append({"t": text, "img": img, "w": written, "a": answer, "acc": accepted, "md": q.md, "opts": options,
                    "label": name, "sec": meta["sec"], "k": k, "max": most})
    return key


@router.post("/api/tests")
async def create_test(body: NewTest, acc=Depends(auth.teacher)):
    key = build_key(body)
    pub = body.pub and not body.printed
    if pub and body.subj not in config.SUBJECTS:
        raise HTTPException(400, "Fanni tanlang.")
    images = [q["img"] for q in key if q["img"]]
    if len(images) != len(set(images)):
        raise HTTPException(400, "Bitta rasm ikki savolga qoʻyilgan.")
    async with db.pool.acquire() as conn, conn.transaction():
        cost = (await db.settings(conn))["tc"]
        me = await conn.fetchrow(
            "UPDATE accounts SET cr = cr - $1 WHERE id = $2 AND cr >= $1 RETURNING *", cost, acc["id"])
        if not me:
            raise HTTPException(400, "Kredit yetarli emas. Hisob boʻlimida kredit paketini sotib oling.")
        code = None
        while not code:
            code = await conn.fetchval(
                """INSERT INTO tests(code, owner_id, title, minutes, n, k, printed, pub, is_open,
                                     subj, pay, price, key, tpl)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                   ON CONFLICT (code) DO NOTHING RETURNING code""",
                f"RASH-{100000 + secrets.randbelow(900000)}", me["id"], body.title.strip() or "Nomsiz test",
                body.min, len(key), 6 if body.tpl else body.k, body.printed, pub, body.open,
                body.subj if pub else "", body.pay if pub else "", body.price if pub else 0, key, body.tpl)
        if images:
            done = await conn.execute(
                "UPDATE images SET test_code = $1 WHERE id = ANY($2) AND owner_id = $3 AND test_code IS NULL",
                code, images, me["id"])
            if int(done.split()[-1]) != len(images):
                raise HTTPException(400, "Baʼzi rasmlar topilmadi. Ularni qayta yuklang.")
    return {"code": code, "cost": cost, "account": account(me)}


@router.get("/api/my/tests")
async def my_tests(acc=Depends(auth.teacher)):
    rows = await db.pool.fetch(TESTS_SQL + " WHERE t.owner_id = $1 ORDER BY t.created_at DESC", acc["id"])
    counts = dict(await db.pool.fetch(
        """SELECT a.test_code, COUNT(*) FROM attempts a JOIN tests t ON t.code = a.test_code
           WHERE t.owner_id = $1 AND a.submitted_at IS NOT NULL GROUP BY a.test_code""", acc["id"]))
    return [{**card(r), "attempts": counts.get(r["code"], 0)} for r in rows]


@router.get("/api/my/tests/{code}/attempts")
async def test_attempts(code: str, acc=Depends(auth.teacher)):
    test = await db.pool.fetchrow(
        "SELECT title, key, tpl FROM tests WHERE code = $1 AND owner_id = $2", code, acc["id"])
    if not test:
        raise HTTPException(404, "Test topilmadi.")
    rows = await db.pool.fetch(
        """SELECT a.id, a.answers, a.accepted, a.scores, a.submitted_at, s.name FROM attempts a
           JOIN accounts s ON s.id = a.account_id
           WHERE a.test_code = $1 AND a.submitted_at IS NOT NULL
           ORDER BY a.submitted_at DESC LIMIT 300""", code)
    cal = await calibration(db.pool, code)
    items = []
    for r in rows:
        review, ok = checking.grade(test["key"], r["answers"], r["accepted"], r["scores"])
        # Yozilgan, lekin xato deb olingan yozma javoblar: o'qituvchi ko'rib chiqishi mumkin.
        check = sum(1 for q in review if q["w"] and not q["max"] and not q["ok"] and (q["my"] or "").strip())
        pending = sum(1 for q in review if q["max"] and q["got"] is None)
        items.append({"id": r["id"], "name": r["name"], "ok": ok, "n": sum(1 for q in review if not q["max"]),
                      "check": check, "pending": pending, "at": r["submitted_at"].isoformat(),
                      "score": scoring.summary(test["tpl"], review, cal) if cal else None})
    return {"title": test["title"], "items": items}


ATTEMPT_SQL = """SELECT a.id, a.answers, a.accepted, a.scores, s.name, t.code, t.title, t.k, t.key, t.tpl
FROM attempts a JOIN tests t ON t.code = a.test_code JOIN accounts s ON s.id = a.account_id
WHERE a.id = $1 AND t.owner_id = $2 AND a.submitted_at IS NOT NULL"""


async def attempt_view(conn, row, accepted: list[int], scores: dict) -> dict:
    review, ok = checking.grade(row["key"], row["answers"], accepted, scores)
    cal = await calibration(conn, row["code"])
    return {"id": row["id"], "name": row["name"], "code": row["code"], "title": row["title"], "k": row["k"],
            "ok": ok, "n": sum(1 for q in review if not q["max"]), "review": review,
            "score": scoring.summary(row["tpl"], review, cal) if cal else None}


@router.get("/api/my/attempts/{attempt_id}")
async def attempt_detail(attempt_id: int, acc=Depends(auth.teacher)):
    row = await db.pool.fetchrow(ATTEMPT_SQL, attempt_id, acc["id"])
    if not row:
        raise HTTPException(404, "Natija topilmadi.")
    return await attempt_view(db.pool, row, row["accepted"], row["scores"])


class Mark(BaseModel):
    index: int = Field(ge=0, le=119)
    ok: bool


@router.post("/api/my/attempts/{attempt_id}/mark")
async def mark(attempt_id: int, body: Mark, acc=Depends(auth.teacher)):
    async with db.pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(ATTEMPT_SQL + " FOR UPDATE OF a", attempt_id, acc["id"])
        if not row:
            raise HTTPException(404, "Natija topilmadi.")
        review, _ = checking.grade(row["key"], row["answers"], [])
        if body.index >= len(review):
            raise HTTPException(400, "Bunday savol yoʻq.")
        q = review[body.index]
        if not q["w"] or q["max"] or q["auto"] or not (q["my"] or "").strip():
            raise HTTPException(400, "Faqat xato deb olingan yozma javobni oʻzgartirish mumkin.")
        accepted = sorted(set(row["accepted"]) - {body.index} | ({body.index} if body.ok else set()))
        _, ok = checking.grade(row["key"], row["answers"], accepted)
        await conn.execute("UPDATE attempts SET accepted = $1, ok = $2 WHERE id = $3", accepted, ok, attempt_id)
        return await attempt_view(conn, row, accepted, row["scores"])


class Score(BaseModel):
    index: int = Field(ge=0, le=119)
    points: float = Field(ge=0, le=100)


@router.post("/api/my/attempts/{attempt_id}/score")
async def score(attempt_id: int, body: Score, acc=Depends(auth.teacher)):
    """Yozma ish / esseni o'qituvchi baholaydi."""
    async with db.pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(ATTEMPT_SQL + " FOR UPDATE OF a", attempt_id, acc["id"])
        if not row:
            raise HTTPException(404, "Natija topilmadi.")
        most = row["key"][body.index].get("max") if body.index < len(row["key"]) else 0
        if not most:
            raise HTTPException(400, "Bu savolga qoʻlda ball qoʻyilmaydi.")
        if body.points > most:
            raise HTTPException(400, f"Ball {most:g} dan oshmasin.")
        scores = {**row["scores"], str(body.index): round(body.points, 1)}
        await conn.execute("UPDATE attempts SET scores = $1 WHERE id = $2", scores, attempt_id)
        return await attempt_view(conn, row, row["accepted"], scores)


class Open(BaseModel):
    open: bool


@router.post("/api/my/tests/{code}/open")
async def set_open(code: str, body: Open, acc=Depends(auth.teacher)):
    done = await db.pool.execute(
        "UPDATE tests SET is_open = $1 WHERE code = $2 AND owner_id = $3", body.open, code, acc["id"])
    if done.endswith(" 0"):
        raise HTTPException(404, "Test topilmadi.")
    return {"ok": True}

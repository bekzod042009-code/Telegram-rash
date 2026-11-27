"""O'qituvchi: rasm yuklash, test yaratish, testlarim."""
import asyncio
import io
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from .. import auth, checking, config, db
from .shared import TESTS_SQL, account, card

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
    t: str = Field(default="", max_length=2000)
    img: str | None = Field(default=None, max_length=64)
    w: bool = False
    a: str | None = Field(default=None, max_length=1)
    acc: list[str] = Field(default_factory=list, max_length=20)
    md: Literal["key", "exact", "fuzzy"] = "key"
    opts: list[str] = Field(default_factory=list, max_length=6)


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
    questions: list[Question] = Field(min_length=1, max_length=100)


def build_key(body: NewTest) -> list[dict]:
    key = []
    for i, q in enumerate(body.questions, 1):
        text = "" if body.printed else q.t.strip()
        img = None if body.printed else q.img
        if not body.printed and not text and not img:
            raise HTTPException(400, f"{i}-savolda matn yoki rasm yoʻq.")
        accepted = []
        options = []
        answer = None
        if q.w:
            accepted = [a.strip() for a in q.acc if checking.norm(a)]
            if not accepted or any(len(a) > 200 for a in accepted):
                raise HTTPException(400, f"{i}-savolda yozma javob notoʻgʻri.")
        else:
            if not q.a or q.a not in config.LETTERS[:body.k]:
                raise HTTPException(400, f"{i}-savolda javob belgilanmagan.")
            answer = q.a
            if not body.printed:
                options = [o.strip() for o in q.opts[:body.k]]
                options += [""] * (body.k - len(options))
                if any(len(o) > 500 for o in options):
                    raise HTTPException(400, f"{i}-savolda variant matni juda uzun.")
                # Rasmli savolda variantlar rasmning ichida bo'lishi mumkin.
                if not img and not all(options):
                    raise HTTPException(400, f"{i}-savolda variant matni yoʻq.")
        key.append({"t": text, "img": img, "w": q.w, "a": answer, "acc": accepted, "md": q.md, "opts": options})
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
                                     subj, pay, price, key)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                   ON CONFLICT (code) DO NOTHING RETURNING code""",
                f"RASH-{100000 + secrets.randbelow(900000)}", me["id"], body.title.strip() or "Nomsiz test",
                body.min, len(key), body.k, body.printed, pub, body.open,
                body.subj if pub else "", body.pay if pub else "", body.price if pub else 0, key)
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
        "SELECT title, key FROM tests WHERE code = $1 AND owner_id = $2", code, acc["id"])
    if not test:
        raise HTTPException(404, "Test topilmadi.")
    rows = await db.pool.fetch(
        """SELECT a.id, a.answers, a.accepted, a.submitted_at, s.name FROM attempts a
           JOIN accounts s ON s.id = a.account_id
           WHERE a.test_code = $1 AND a.submitted_at IS NOT NULL
           ORDER BY a.submitted_at DESC LIMIT 300""", code)
    items = []
    for r in rows:
        review, ok = checking.grade(test["key"], r["answers"], r["accepted"])
        # Yozilgan, lekin xato deb olingan yozma javoblar: o'qituvchi ko'rib chiqishi mumkin.
        check = sum(1 for q in review if q["w"] and not q["ok"] and (q["my"] or "").strip())
        items.append({"id": r["id"], "name": r["name"], "ok": ok, "n": len(review), "check": check,
                      "at": r["submitted_at"].isoformat()})
    return {"title": test["title"], "items": items}


ATTEMPT_SQL = """SELECT a.id, a.answers, a.accepted, s.name, t.code, t.title, t.k, t.key
FROM attempts a JOIN tests t ON t.code = a.test_code JOIN accounts s ON s.id = a.account_id
WHERE a.id = $1 AND t.owner_id = $2 AND a.submitted_at IS NOT NULL"""


def attempt_view(row, accepted: list[int]) -> dict:
    review, ok = checking.grade(row["key"], row["answers"], accepted)
    return {"id": row["id"], "name": row["name"], "code": row["code"], "title": row["title"], "k": row["k"],
            "ok": ok, "n": len(review), "review": review}


@router.get("/api/my/attempts/{attempt_id}")
async def attempt_detail(attempt_id: int, acc=Depends(auth.teacher)):
    row = await db.pool.fetchrow(ATTEMPT_SQL, attempt_id, acc["id"])
    if not row:
        raise HTTPException(404, "Natija topilmadi.")
    return attempt_view(row, row["accepted"])


class Mark(BaseModel):
    index: int = Field(ge=0, le=99)
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
        if not q["w"] or q["auto"] or not (q["my"] or "").strip():
            raise HTTPException(400, "Faqat xato deb olingan yozma javobni oʻzgartirish mumkin.")
        accepted = set(row["accepted"]) - {body.index}
        if body.ok:
            accepted.add(body.index)
        view = attempt_view(row, sorted(accepted))
        await conn.execute("UPDATE attempts SET accepted = $1, ok = $2 WHERE id = $3",
                           sorted(accepted), view["ok"], attempt_id)
    return view


class Open(BaseModel):
    open: bool


@router.post("/api/my/tests/{code}/open")
async def set_open(code: str, body: Open, acc=Depends(auth.teacher)):
    done = await db.pool.execute(
        "UPDATE tests SET is_open = $1 WHERE code = $2 AND owner_id = $3", body.open, code, acc["id"])
    if done.endswith(" 0"):
        raise HTTPException(404, "Test topilmadi.")
    return {"ok": True}

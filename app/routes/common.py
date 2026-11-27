"""Kirish, ro'yxatdan o'tish, arizalar va rasmlarni ko'rsatish."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .. import auth, bot, config, db
from .shared import account, request_row

router = APIRouter()
MAX_PENDING_REQUESTS = 5


@router.get("/api/me")
async def me(user: dict = Depends(auth.tg_user)):
    rows = await db.pool.fetch("SELECT * FROM accounts WHERE tg_id = $1", user["id"])
    accounts = {r["role"]: account(r) for r in rows}
    return {"tg_id": user["id"], "first_name": user.get("first_name", ""), "last_name": user.get("last_name", ""),
            "is_admin": user["id"] in config.ADMIN_IDS, "accounts": accounts,
            "cfg": await db.settings(), "subjects": config.SUBJECTS,
            "bot": bot.username, "payment_info": config.PAYMENT_INFO}


class Register(BaseModel):
    role: Literal["t", "s"]
    first: str = Field(max_length=60)
    last: str = Field(max_length=60)


@router.post("/api/register")
async def register(body: Register, user: dict = Depends(auth.tg_user)):
    first, last = body.first.strip(), body.last.strip()
    if not first or not last:
        raise HTTPException(400, "Ism va familiyani kiriting.")
    referrer = None
    async with db.pool.acquire() as conn, conn.transaction():
        cfg = await db.settings(conn)
        row = await conn.fetchrow(
            """INSERT INTO accounts(tg_id, role, name, cr) VALUES ($1, $2, $3, $4)
               ON CONFLICT (tg_id, role) DO NOTHING RETURNING *""",
            user["id"], body.role, f"{first} {last}", cfg["tw" if body.role == "t" else "sw"])
        if not row:
            row = await conn.fetchrow(
                "SELECT * FROM accounts WHERE tg_id = $1 AND role = $2", user["id"], body.role)
        else:
            # Taklif mukofoti bir marta, taklif qilingan odam birinchi ro'yxatdan o'tganda beriladi.
            ref = await conn.fetchrow(
                "SELECT * FROM referrals WHERE invitee_tg = $1 AND NOT rewarded FOR UPDATE", user["id"])
            if ref:
                target = await conn.fetchval(
                    "SELECT id FROM accounts WHERE tg_id = $1 ORDER BY role LIMIT 1", ref["referrer_tg"])
                if target:
                    await conn.execute("UPDATE accounts SET cr = cr + $1 WHERE id = $2", cfg["ref"], target)
                    await conn.execute("UPDATE referrals SET rewarded = TRUE WHERE invitee_tg = $1", user["id"])
                    referrer = (ref["referrer_tg"], cfg["ref"])
    if referrer:
        bot.notify([referrer[0]], f"Doʻstingiz qoʻshildi: +{referrer[1]} kredit.")
    return account(row)


@router.get("/api/requests")
async def my_requests(acc=Depends(auth.any_account)):
    rows = await db.pool.fetch(
        "SELECT * FROM requests WHERE account_id = $1 ORDER BY id DESC LIMIT 30", acc["id"])
    return {"account": account(acc), "items": [request_row(r) for r in rows]}


class NewRequest(BaseModel):
    type: Literal["topup", "pack", "withdraw"]
    amount: int = Field(default=0, ge=0, le=10_000_000)
    credits: int = Field(default=0, ge=0, le=1_000_000)


@router.post("/api/requests")
async def new_request(body: NewRequest, acc=Depends(auth.any_account)):
    async with db.pool.acquire() as conn, conn.transaction():
        acc = await conn.fetchrow("SELECT * FROM accounts WHERE id = $1 FOR UPDATE", acc["id"])
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM requests WHERE account_id = $1 AND status = 'new'", acc["id"])
        if pending >= MAX_PENDING_REQUESTS:
            raise HTTPException(400, "Kutilayotgan arizalar koʻp. Admin javobini kuting.")
        amount, credits = body.amount, 0
        if body.type == "topup":
            if acc["role"] != "s" or amount < 1000:
                raise HTTPException(400, "Summa notoʻgʻri.")
        elif body.type == "pack":
            cfg = await db.settings(conn)
            pack = next((p for p in cfg["pk"] if p["c"] == body.credits), None)
            if not pack:
                raise HTTPException(400, "Bunday paket yoʻq. Sahifani yangilang.")
            amount, credits = pack["p"], pack["c"]
        else:
            if acc["role"] != "t" or acc["earn"] <= 0:
                raise HTTPException(400, "Yechish uchun daromad yoʻq.")
            amount = acc["earn"]
            await conn.execute("UPDATE accounts SET earn = 0 WHERE id = $1", acc["id"])
        await conn.execute("INSERT INTO requests(account_id, type, amount, credits) VALUES ($1, $2, $3, $4)",
                           acc["id"], body.type, amount, credits)
        acc = await conn.fetchrow("SELECT * FROM accounts WHERE id = $1", acc["id"])
    label = {"topup": "balans toʻldirish", "pack": f"{credits} kredit paketi", "withdraw": "pul yechish"}
    bot.notify(config.ADMIN_IDS,
               f"Yangi ariza: {label[body.type]}, {amount} soʻm\n{acc['name']} (ID {acc['tg_id']})")
    return {"account": account(acc)}


@router.get("/img/{image_id}")
async def image(image_id: str):
    data = await db.pool.fetchval("SELECT data FROM images WHERE id = $1", image_id)
    if data is None:
        raise HTTPException(404, "Rasm topilmadi.")
    return Response(data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=31536000, immutable"})

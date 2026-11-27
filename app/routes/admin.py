"""Admin: faqat ADMIN_IDS dagi Telegram ID lar uchun."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import auth, bot, db
from .shared import TESTS_SQL, account, card, request_row

router = APIRouter(prefix="/api/admin", dependencies=[Depends(auth.admin)])


@router.get("/tests")
async def tests():
    rows = await db.pool.fetch(TESTS_SQL + " ORDER BY t.created_at DESC LIMIT 200")
    return [{**card(r), "owner": r["owner_name"], "key": r["key"]} for r in rows]


@router.get("/earn")
async def earn():
    teachers = await db.pool.fetch(
        """SELECT a.*,
             (SELECT COUNT(*) FROM tests t WHERE t.owner_id = a.id) AS tests,
             (SELECT COALESCE(SUM(sold), 0)::bigint FROM tests t WHERE t.owner_id = a.id) AS sales
           FROM accounts a WHERE role = 't' ORDER BY earn DESC, id DESC""")
    pending = await db.pool.fetch(
        """SELECT r.*, a.name, a.tg_id, a.role FROM requests r JOIN accounts a ON a.id = r.account_id
           WHERE status = 'new' ORDER BY r.id LIMIT 100""")
    return {"teachers": [{**account(r), "tests": r["tests"], "sales": r["sales"]} for r in teachers],
            "requests": [{**request_row(r), "name": r["name"], "tg_id": r["tg_id"], "role": r["role"]}
                         for r in pending]}


class Decision(BaseModel):
    approve: bool


@router.post("/requests/{request_id}")
async def decide(request_id: int, body: Decision):
    async with db.pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            "UPDATE requests SET status = $1 WHERE id = $2 AND status = 'new' RETURNING *",
            "done" if body.approve else "rejected", request_id)
        if not row:
            raise HTTPException(409, "Ariza allaqachon koʻrib chiqilgan.")
        column = None
        if body.approve and row["type"] == "topup":
            column, value = "bal", row["amount"]
        elif body.approve and row["type"] == "pack":
            column, value = "cr", row["credits"]
        elif not body.approve and row["type"] == "withdraw":
            column, value = "earn", row["amount"]
        if column:
            await conn.execute(f"UPDATE accounts SET {column} = {column} + $1 WHERE id = $2",
                               value, row["account_id"])
        tg_id = await conn.fetchval("SELECT tg_id FROM accounts WHERE id = $1", row["account_id"])
    what = {"topup": "Balans toʻldirish", "pack": "Kredit paketi", "withdraw": "Pul yechish"}[row["type"]]
    bot.notify([tg_id], f"{what} arizangiz ({row['amount']} soʻm) "
                        + ("tasdiqlandi." if body.approve else "rad etildi."))
    return {"ok": True}


class Pack(BaseModel):
    c: int = Field(ge=1, le=1_000_000)
    p: int = Field(ge=0, le=100_000_000)


class Settings(BaseModel):
    tc: int = Field(ge=0, le=1_000_000)
    tw: int = Field(ge=0, le=1_000_000)
    sw: int = Field(ge=0, le=1_000_000)
    ref: int = Field(ge=0, le=1_000_000)
    com: int = Field(ge=0, le=100)
    pk: list[Pack] = Field(max_length=12)


@router.put("/settings")
async def save_settings(body: Settings):
    data = body.model_dump()
    if len({p["c"] for p in data["pk"]}) != len(data["pk"]):
        raise HTTPException(400, "Paketlarda kredit miqdori takrorlanmasin.")
    data["pk"].sort(key=lambda p: -p["c"])
    await db.pool.execute("UPDATE settings SET data = $1 WHERE id = 1", data)
    return data


@router.get("/users")
async def users():
    rows = await db.pool.fetch("SELECT * FROM accounts ORDER BY id DESC LIMIT 200")
    return [account(r) for r in rows]


@router.get("/users/{tg_id}")
async def user(tg_id: int):
    if not 0 < tg_id < 2**62:
        return []
    rows = await db.pool.fetch("SELECT * FROM accounts WHERE tg_id = $1 ORDER BY role", tg_id)
    return [account(r) for r in rows]


class Give(BaseModel):
    account_id: int = Field(ge=1, le=2_000_000_000)
    kind: Literal["cr", "bal"] = "cr"
    amount: int = Field(ge=1, le=100_000_000)


@router.post("/give")
async def give(body: Give):
    row = await db.pool.fetchrow(
        f"UPDATE accounts SET {body.kind} = {body.kind} + $1 WHERE id = $2 RETURNING *",
        body.amount, body.account_id)
    if not row:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    unit = "kredit" if body.kind == "cr" else "soʻm"
    bot.notify([row["tg_id"]], f"Hisobingizga {body.amount} {unit} qoʻshildi.")
    return account(row)

"""O'quvchi: qidirish, sotib olish, yechish, baholash. Javob kaliti faqat serverda."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import auth, checking, db
from .shared import TESTS_SQL, account, card

router = APIRouter()
GRACE = 60  # soniya: sekin internet uchun
BEST_FIRST = " ORDER BY rating DESC, votes DESC, t.created_at DESC"


async def find_test(conn, code: str):
    row = await conn.fetchrow(TESTS_SQL + " WHERE t.code = $1", code.strip().upper())
    if not row:
        raise HTTPException(404, "Test topilmadi.")
    return row


async def has_access(conn, test, acc) -> bool:
    if not test["pub"] or test["price"] <= 0 or test["owner_tg"] == acc["tg_id"]:
        return True
    return bool(await conn.fetchval(
        "SELECT 1 FROM purchases WHERE account_id = $1 AND test_code = $2", acc["id"], test["code"]))


def ensure_open(test, acc):
    if not test["is_open"] and test["owner_tg"] != acc["tg_id"]:
        raise HTTPException(403, "Bu test hozir yopiq.")


@router.get("/api/search")
async def search(q: str = "", acc=Depends(auth.student)):
    needle = " ".join(checking.norm(q[:100]))
    if not needle:
        raise HTTPException(400, "Kod yoki fan nomini kiriting.")
    rows = await db.pool.fetch(TESTS_SQL + " WHERE t.pub AND t.is_open" + BEST_FIRST)
    found = (r for r in rows if needle in " ".join(checking.norm(r["subj"] + " " + r["title"])))
    return [card(r) for r, _ in zip(found, range(50))]


@router.get("/api/sections")
async def sections(acc=Depends(auth.student)):
    rows = await db.pool.fetch("SELECT subj, COUNT(*) AS c FROM tests WHERE pub AND is_open GROUP BY subj")
    return {r["subj"]: r["c"] for r in rows}


@router.get("/api/section")
async def section(subj: str, acc=Depends(auth.student)):
    rows = await db.pool.fetch(
        TESTS_SQL + " WHERE t.pub AND t.is_open AND t.subj = $1" + BEST_FIRST + " LIMIT 100", subj)
    return [card(r) for r in rows]


@router.get("/api/tests/{code}")
async def test_info(code: str, acc=Depends(auth.student)):
    async with db.pool.acquire() as conn:
        test = await find_test(conn, code)
        ensure_open(test, acc)
        return {**card(test), "need_buy": not await has_access(conn, test, acc)}


@router.post("/api/tests/{code}/buy")
async def buy(code: str, acc=Depends(auth.student)):
    async with db.pool.acquire() as conn, conn.transaction():
        test = await find_test(conn, code)
        ensure_open(test, acc)
        if not await has_access(conn, test, acc):
            fresh = await conn.fetchval(
                """INSERT INTO purchases(account_id, test_code, price, pay) VALUES ($1, $2, $3, $4)
                   ON CONFLICT DO NOTHING RETURNING 1""", acc["id"], test["code"], test["price"], test["pay"])
            if fresh:
                column = "cr" if test["pay"] == "c" else "bal"
                paid = await conn.fetchval(
                    f"UPDATE accounts SET {column} = {column} - $1 WHERE id = $2 AND {column} >= $1 RETURNING id",
                    test["price"], acc["id"])
                if not paid:
                    raise HTTPException(400, "Kredit yetarli emas. Balans boʻlimida kredit oling."
                                        if column == "cr" else
                                        "Balansda mablagʻ yetarli emas. Balans boʻlimida toʻldiring.")
                com = (await db.settings(conn))["com"]
                share = (test["price"] * com + 50) // 100
                income = "ecr" if test["pay"] == "c" else "earn"
                await conn.execute(f"UPDATE accounts SET {income} = {income} + $1 WHERE id = $2",
                                   share, test["owner_id"])
                await conn.execute("UPDATE tests SET sold = sold + 1 WHERE code = $1", test["code"])
        me = await conn.fetchrow("SELECT * FROM accounts WHERE id = $1", acc["id"])
    return {"account": account(me)}


@router.post("/api/tests/{code}/start")
async def start(code: str, acc=Depends(auth.student)):
    async with db.pool.acquire() as conn, conn.transaction():
        # Bir vaqtda ikki marta bosilsa ham bitta urinish ochiladi.
        await conn.execute("SELECT 1 FROM accounts WHERE id = $1 FOR UPDATE", acc["id"])
        test = await find_test(conn, code)
        ensure_open(test, acc)
        if not await has_access(conn, test, acc):
            raise HTTPException(402, "Avval testni sotib oling.")
        seconds = test["minutes"] * 60
        attempt = await conn.fetchrow(
            """SELECT id, EXTRACT(EPOCH FROM clock_timestamp() - started_at)::float AS used FROM attempts
               WHERE account_id = $1 AND test_code = $2 AND submitted_at IS NULL
               ORDER BY id DESC LIMIT 1""", acc["id"], test["code"])
        if attempt and attempt["used"] < seconds:
            attempt_id, left = attempt["id"], seconds - attempt["used"]
        else:
            attempt_id = await conn.fetchval(
                "INSERT INTO attempts(account_id, test_code) VALUES ($1, $2) RETURNING id",
                acc["id"], test["code"])
            left = seconds
    questions = [{"t": q["t"], "img": q["img"], "w": q["w"]} for q in test["key"]]
    return {**card(test), "attempt": attempt_id, "left": int(left), "questions": questions}


class Submit(BaseModel):
    answers: list[str | None] = Field(max_length=100)


@router.post("/api/attempts/{attempt_id}/submit")
async def submit(attempt_id: int, body: Submit, acc=Depends(auth.student)):
    if any(a and len(a) > 500 for a in body.answers):
        raise HTTPException(400, "Javob juda uzun.")
    async with db.pool.acquire() as conn, conn.transaction():
        attempt = await conn.fetchrow(
            """SELECT *, EXTRACT(EPOCH FROM clock_timestamp() - started_at)::float AS used
               FROM attempts WHERE id = $1 AND account_id = $2 FOR UPDATE""", attempt_id, acc["id"])
        if not attempt:
            raise HTTPException(404, "Urinish topilmadi.")
        if attempt["submitted_at"]:
            raise HTTPException(409, "Javoblar allaqachon yuborilgan. Natijalar boʻlimini oching.")
        test = await find_test(conn, attempt["test_code"])
        if attempt["used"] > test["minutes"] * 60 + GRACE:
            raise HTTPException(410, "Vaqt tugagan, javoblar qabul qilinmadi. Testni qayta boshlang.")
        review, ok = [], 0
        for i, q in enumerate(test["key"]):
            mine = body.answers[i] if i < len(body.answers) else None
            right = checking.check(mine or "", q["acc"], q["md"]) if q["w"] else mine == q["a"]
            ok += right
            review.append({"t": q["t"], "img": q["img"], "w": q["w"], "a": q["a"], "acc": q["acc"],
                           "my": mine, "ok": right})
        await conn.execute(
            "UPDATE attempts SET submitted_at = now(), answers = $1, ok = $2 WHERE id = $3",
            body.answers, ok, attempt_id)
        mine_rating = await conn.fetchval(
            "SELECT stars FROM ratings WHERE account_id = $1 AND test_code = $2", acc["id"], test["code"])
    return {"ok": ok, "n": test["n"], "k": test["k"], "review": review, "my_rating": mine_rating or 0,
            "can_rate": test["owner_tg"] != acc["tg_id"]}


class Rating(BaseModel):
    stars: int = Field(ge=1, le=5)


@router.post("/api/tests/{code}/rate")
async def rate(code: str, body: Rating, acc=Depends(auth.student)):
    async with db.pool.acquire() as conn:
        test = await find_test(conn, code)
        if test["owner_tg"] == acc["tg_id"]:
            raise HTTPException(400, "Oʻz testingizni baholay olmaysiz.")
        solved = await conn.fetchval(
            "SELECT 1 FROM attempts WHERE account_id = $1 AND test_code = $2 AND submitted_at IS NOT NULL",
            acc["id"], test["code"])
        if not solved:
            raise HTTPException(400, "Avval testni yeching.")
        await conn.execute(
            """INSERT INTO ratings(account_id, test_code, stars) VALUES ($1, $2, $3)
               ON CONFLICT (account_id, test_code) DO UPDATE SET stars = $3""",
            acc["id"], test["code"], body.stars)
    return {"ok": True}


@router.get("/api/results")
async def results(acc=Depends(auth.student)):
    rows = await db.pool.fetch(
        """SELECT t.title, t.code, t.n, a.ok FROM attempts a JOIN tests t ON t.code = a.test_code
           WHERE a.account_id = $1 AND a.submitted_at IS NOT NULL
           ORDER BY a.submitted_at DESC LIMIT 100""", acc["id"])
    return [dict(r) for r in rows]

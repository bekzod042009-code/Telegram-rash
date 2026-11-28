"""Bir nechta bo'limda ishlatiladigan so'rovlar."""
import asyncio

from .. import scoring, templates

TESTS_SQL = """
SELECT t.*, o.tg_id AS owner_tg, o.name AS owner_name,
       COALESCE(r.avg, 0)::float AS rating, COALESCE(r.cnt, 0)::int AS votes
FROM tests t
JOIN accounts o ON o.id = t.owner_id
LEFT JOIN (SELECT test_code, AVG(stars) AS avg, COUNT(*) AS cnt FROM ratings GROUP BY test_code) r
  ON r.test_code = t.code
"""


def card(t) -> dict:
    """Test haqida umumiy ma'lumot (javoblarsiz)."""
    tpl = templates.TEMPLATES.get(t["tpl"])
    return {"tpl": t["tpl"], "tpl_name": tpl["name"] if tpl else "", "qn": len(tpl["slots"]) if tpl else t["n"],
            "code": t["code"], "title": t["title"], "min": t["minutes"], "n": t["n"], "k": t["k"],
            "printed": t["printed"], "pub": t["pub"], "open": t["is_open"], "subj": t["subj"],
            "pay": t["pay"], "price": t["price"], "sold": t["sold"],
            "rating": t["rating"], "votes": t["votes"]}


def account(a) -> dict:
    return {k: a[k] for k in ("id", "tg_id", "role", "name", "cr", "bal", "earn", "ecr")}


def request_row(r) -> dict:
    return {k: r[k] for k in ("id", "type", "amount", "credits", "status")}


async def calibration(conn, code: str) -> dict | None:
    """Qolipli test uchun Rash modeli: har bir o'quvchining birinchi urinishi (muallifsiz)."""
    test = await conn.fetchrow("SELECT tpl, key, owner_id FROM tests WHERE code = $1", code)
    if not test or not test["tpl"]:
        return None
    rows = await conn.fetch(
        """SELECT DISTINCT ON (a.account_id) a.answers, a.accepted FROM attempts a
           JOIN accounts s ON s.id = a.account_id
           JOIN accounts o ON o.id = $2
           WHERE a.test_code = $1 AND a.submitted_at IS NOT NULL AND s.tg_id <> o.tg_id
           ORDER BY a.account_id, a.id""", code, test["owner_id"])
    # Hisob og'ir bo'lishi mumkin: server va botni to'xtatib qo'ymasin.
    return await asyncio.to_thread(scoring.calibrate, test["key"], test["tpl"], rows)

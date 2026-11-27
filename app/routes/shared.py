"""Bir nechta bo'limda ishlatiladigan so'rovlar."""

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
    return {"code": t["code"], "title": t["title"], "min": t["minutes"], "n": t["n"], "k": t["k"],
            "printed": t["printed"], "pub": t["pub"], "open": t["is_open"], "subj": t["subj"],
            "pay": t["pay"], "price": t["price"], "sold": t["sold"],
            "rating": t["rating"], "votes": t["votes"]}


def account(a) -> dict:
    return {k: a[k] for k in ("id", "tg_id", "role", "name", "cr", "bal", "earn", "ecr")}


def request_row(r) -> dict:
    return {k: r[k] for k in ("id", "type", "amount", "credits", "status")}

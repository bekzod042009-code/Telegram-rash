"""Xom ball, Rash modeli (0-75) va sertifikat darajalari."""
import math

from . import checking, templates

MIN_PEOPLE = 10  # shundan kam ishtirokchida Rash balli hisoblanmaydi
GRADES = ((70, "A+"), (65, "A"), (60, "B+"), (55, "B"), (50, "C+"), (46, "C"))
CEFR = ((65, "C1"), (51, "B2"), (38, "B1"))


def _p(x: float) -> float:
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, x))))


def _theta(raw: float, items: list[float]) -> float:
    m = len(items)
    raw = max(0.3, min(m - 0.3, raw))
    t = math.log(raw / (m - raw))
    for _ in range(60):
        ps = [_p(t - b) for b in items]
        step = (raw - sum(ps)) / max(1e-9, sum(p * (1 - p) for p in ps))
        step = max(-1.0, min(1.0, step))
        t += step
        if abs(step) < 1e-6:
            break
    return t


def rasch(rows: list[list[bool]]) -> dict:
    """Dixotomik Rash modeli (JMLE). rows: har bir ishtirokchining to'g'ri/xato qatori."""
    m = len(rows[0])
    raws = [sum(r) for r in rows]
    core = [r for r, s in zip(rows, raws) if 0 < s < m] or rows
    n = len(core)
    right = [max(0.3, min(n - 0.3, sum(r[i] for r in core))) for i in range(m)]
    items = [math.log((n - s) / s) for s in right]
    groups: dict[int, int] = {}
    for r in core:
        groups[sum(r)] = groups.get(sum(r), 0) + 1
    for _ in range(100):
        mean = sum(items) / m
        items = [b - mean for b in items]
        people = [(_theta(s, items), c) for s, c in groups.items()]
        moved = 0.0
        for i in range(m):
            ps = [(_p(t - items[i]), c) for t, c in people]
            step = (sum(p * c for p, c in ps) - right[i]) / max(1e-9, sum(p * (1 - p) * c for p, c in ps))
            step = max(-1.0, min(1.0, step))
            items[i] += step
            moved = max(moved, abs(step))
        if moved < 1e-4:
            break
    by_raw = {s: _theta(s, items) for s in set(raws)}
    abilities = [by_raw[s] for s in raws]
    mu = sum(abilities) / len(abilities)
    sd = math.sqrt(sum((t - mu) ** 2 for t in abilities) / len(abilities))
    return {"items": items, "mu": mu, "sd": sd}


def scale(raw: int, model: dict) -> float:
    """T = 50 + 10Z, 0..75 oralig'ida."""
    if model["sd"] < 1e-6:
        return 50.0
    z = (_theta(raw, model["items"]) - model["mu"]) / model["sd"]
    return round(max(0.0, min(75.0, 50 + 10 * z)), 1)


def _groups(key: list[dict], tpl: str) -> dict[str, list[int]]:
    """Rash alohida hisoblanadigan savol guruhlari."""
    auto = [i for i, q in enumerate(key) if not q.get("max")]
    if tpl != templates.MULTI:
        return {"Test": auto}
    names = ("Listening", "Reading", "Use of English")
    return {name: [i for i in auto if key[i].get("sec") == name] for name in names}


def calibrate(key: list[dict], tpl: str, attempts: list) -> dict:
    """attempts: har bir ishtirokchining birinchi urinishi (answers, accepted)."""
    rows = [[q["ok"] for q in checking.grade(key, a["answers"], a["accepted"])[0]] for a in attempts]
    models = {}
    if len(rows) >= MIN_PEOPLE:
        for name, idx in _groups(key, tpl).items():
            if idx:
                models[name] = rasch([[r[i] for i in idx] for r in rows])
    return {"people": len(rows), "models": models}


def grade_name(score: float, table=GRADES) -> str | None:
    return next((g for limit, g in table if score >= limit), None)


def _otm(score: float, multi: bool) -> list[float] | None:
    """OTMga kirishdagi imtiyoz bali: [1-fan (93 dan), 2-fan (63 dan)]."""
    if multi:
        share = 1 if score >= 51 else 0.75 if score >= 38 else 0
    else:
        share = 1 if score >= 65 else score / 75 if score >= 46 else 0
    return [round(93 * share, 1), round(63 * share, 1)] if share else None


def summary(tpl: str, review: list[dict], cal: dict) -> dict:
    """Bitta urinishning ballari. review: checking.grade natijasi."""
    key_like = [{"max": q["max"], "sec": q["sec"]} for q in review]
    auto = [q for q in review if not q["max"]]
    manual = [q for q in review if q["max"]]
    out = {"people": cal["people"], "need": MIN_PEOPLE,
           "raw": round(sum(q["ball"] for q in auto if q["ok"]), 1),
           "raw_max": round(sum(q["ball"] for q in auto), 1),
           "parts": [], "written": None, "final": None, "level": None, "otm": None}
    if manual:
        pending = sum(1 for q in manual if q["got"] is None)
        out["written"] = {"got": round(sum(q["got"] or 0 for q in manual), 1),
                          "max": round(sum(q["max"] for q in manual), 1), "pending": pending}
    scores = {}
    for name, idx in _groups(key_like, tpl).items():
        model = cal["models"].get(name)
        scores[name] = scale(sum(review[i]["ok"] for i in idx), model) if model else None
    if tpl == templates.MULTI:
        for name in ("Writing", "Speaking"):
            qs = [q for q in manual if q["sec"] == name]
            done = qs and all(q["got"] is not None for q in qs)
            scores[name] = round(75 * sum(q["got"] for q in qs) / sum(q["max"] for q in qs), 1) if done else None
        out["parts"] = [{"name": k, "score": v} for k, v in scores.items()]
        four = [scores.get(k) for k in ("Listening", "Reading", "Writing", "Speaking")]
        if all(v is not None for v in four):
            out["final"] = round(sum(four) / 4, 1)
            out["level"] = grade_name(out["final"], CEFR)
    else:
        test = scores.get("Test")
        out["parts"] = [{"name": "Test (Rash)", "score": test}]
        w = out["written"]
        if test is not None and (not w or not w["pending"]):
            # Yozma qismli fanlarda test va yozma ish teng ulushda olinadi (taxminiy usul).
            out["final"] = round((test + 75 * w["got"] / w["max"]) / 2, 1) if w else test
            out["level"] = grade_name(out["final"])
    if out["final"] is not None:
        out["otm"] = _otm(out["final"], tpl == templates.MULTI)
    return out

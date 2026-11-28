"""Milliy sertifikat test qoliplari (UzBMB spetsifikatsiyasi jadvallari asosida).

Savol turlari: y1 - yopiq (A-D), y2 - moslashtirish (A-F), o - qisqa javobli ochiq,
m - yozma ish / esse (o'qituvchi qo'lda baholaydi).
"""

MULTI = "multi"


def _slots(blocks):
    """blocks: (bo'lim nomi, savollar soni, turi)."""
    out = []
    for sec, count, kind in blocks:
        for _ in range(count):
            out.append({"n": len(out) + 1, "type": kind, "sec": sec,
                        "k": 4 if kind == "y1" else 6 if kind == "y2" else 0,
                        "parts": 2 if kind == "o" else 1})
    return out


def _std(ones, opens=10):
    return _slots([*[(s, c, "y1") for s, c in ones], ("Moslashtirish", 3, "y2"),
                   ("Ochiq topshiriqlar", opens, "o")])


def _written(test_blocks):
    return _slots([*[(s, c, "y1") for s, c in test_blocks], ("Moslashtirish", 3, "y2"),
                   ("Qisqa javobli ochiq topshiriqlar", 5, "o"), ("Yozma ish", 3, "m")])


_ONA = _slots([("Imlo qoidalari", 2, "y1"), ("Lugʻat boyligi", 2, "y1"), ("Til birliklari uslubiyati", 2, "y1"),
               ("Grammatika", 5, "y1"), ("Punktuatsiya", 1, "y1"), ("Adabiyot nazariyasi va tarixi", 5, "y1"),
               ("Oʻqish savodxonligi", 15, "y1"), ("Moslashtirish", 3, "y2"),
               ("Lingvistik va badiiy tahlil", 9, "o"), ("Esse", 1, "m")])


def _with_max(slots, values):
    """Yozma ishlarning maksimal balli (o'qituvchi kiritmaydi)."""
    left = list(values)
    return [{**s, "max": left.pop(0)} if s["type"] == "m" else s for s in slots]


TEMPLATES = {
    "mat": {"name": "Matematika", "min": 150, "slots": _std([("Yopiq test", 32)])},
    "fiz": {"name": "Fizika", "min": 150, "slots": _std([
        ("Mexanika", 10), ("Molekulyar fizika va termodinamika", 5), ("Elektr va magnitizm", 10),
        ("Optika. Nisbiylik nazariyasi", 3), ("Kvant fizikasi. Atom va yadro", 3),
        ("Mantiqiy va hayotiy topshiriq", 1)])},
    "kim": {"name": "Kimyo", "min": 180, "slots": _with_max(_written([
        ("Umumiy kimyo", 13), ("Anorganik kimyo", 6), ("Organik kimyo", 10), ("Kimyoviy tahlil", 3)]),
        (25, 25, 25))},
    "bio": {"name": "Biologiya", "min": 180, "slots": _with_max(_written([("Yopiq test", 32)]), (30, 35, 10))},
    "ona": {"name": "Ona tili va adabiyot", "min": 180, "slots": _with_max(_ONA, (75,))},
    "rus": {"name": "Rus tili va adabiyot", "min": 180, "slots": _with_max(_ONA, (75,))},
    "qq": {"name": "Qoraqalpoq tili va adabiyot", "min": 180, "slots": _with_max(_ONA, (75,))},
    "tar": {"name": "Tarix", "min": 90, "slots": _std([("Yopiq test", 32)])},
    "geo": {"name": "Geografiya", "min": 150, "slots": _std([
        ("Fan tizimi va geografik xaritalar", 2), ("Geografik qobiq va okeanlar", 4), ("Materiklar tabiati", 4),
        ("Oʻrta Osiyo va Oʻzbekiston tabiiy geografiyasi", 5), ("Oʻzbekiston va jahon xoʻjaligi", 6),
        ("Jahon mintaqalari va geoekologiya", 4), ("Aholi geografiyasi va demografiya", 3),
        ("Xarita asosidagi topshiriqlar", 4)])},
    MULTI: {"name": "Chet tili", "min": 175, "slots": _with_max(_slots([
        ("Listening", 35, "y1"), ("Reading", 35, "y1"), ("Use of English", 30, "y1"),
        ("Writing", 2, "m"), ("Speaking", 3, "m")]), (25,) * 5)},
}

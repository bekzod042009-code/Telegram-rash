"""Yozma javoblarni tekshirish (prototipdagi norm / lev / check bilan bir xil)."""
import re

CYR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
       "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
       "у": "u", "ф": "f", "х": "x", "ц": "s", "ч": "ch", "ш": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e",
       "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h"}
NUM = {"bir": 1, "birinchi": 1, "ikki": 2, "ikkinchi": 2, "uch": 3, "uchinchi": 3, "tort": 4, "tortinchi": 4,
       "besh": 5, "beshinchi": 5, "olti": 6, "oltinchi": 6, "yetti": 7, "yettinchi": 7, "sakkiz": 8,
       "sakkizinchi": 8, "toqqiz": 9, "toqqizinchi": 9, "on": 10, "oninchi": 10}
ROMAN = {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11,
         "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19, "xx": 20}
APOSTROPHES = re.compile("[ʻʼ'‘’`´]")

# Son ichidagi belgilar vaqtincha almashtiriladi, tinish belgilari tozalanganda yo'qolmasligi uchun.
MINUS, POINT, SLASH = "\ue000", "\ue001", "\ue002"
# Manfiy ishora: boshida yoki = ( [ { | : ; dan keyin ("- 5" ham), yoki bo'shliqdan keyin raqamga yopishgan.
# "5-asr", "1941-1945" kabi chiziqcha ishora hisoblanmaydi.
SIGN = re.compile(r"(^\s*|[=(\[{|:;]\s*)[-−–]\s*(?=[0-9])|(\s)[-−–](?=[0-9])")
# Bitta ajratgichli son: "2,5" yoki "2.5" ("1,2,3" va sanalar bunga kirmaydi).
DECIMAL = re.compile(r"(?<![0-9])(?<![0-9][.,])([0-9]+)[.,]([0-9]+)(?![0-9]|[.,][0-9])")
FRACTION = re.compile(r"(?<![0-9/])([0-9]+)\s*/\s*(?=[0-9]+(?![0-9]|\s*/))")


def _decimal(m: re.Match) -> str:
    tail = m.group(2).rstrip("0")  # 2,50 = 2,5 va 5,0 = 5
    return m.group(1) + (POINT + tail if tail else "")


def norm(s: str) -> list[str]:
    s = APOSTROPHES.sub("", str(s).lower())
    s = "".join(CYR.get(c, c) for c in s)
    s = SIGN.sub(lambda m: (m.group(1) or m.group(2) or "") + " " + MINUS, s)
    s = DECIMAL.sub(_decimal, s)
    s = FRACTION.sub(lambda m: m.group(1) + SLASH, s)
    s = re.sub(rf"[^a-z0-9\s{MINUS}{POINT}{SLASH}]", " ", s)
    words = s.replace(MINUS, "-").replace(POINT, ".").replace(SLASH, "/").split()
    out = []
    for w in words:
        m = re.fullmatch(r"([0-9]+)(chi|nchi|inchi)", w)
        if m:
            out.append(m.group(1))
        elif w in ROMAN:
            out.append(str(ROMAN[w]))
        elif w in NUM:
            out.append(str(NUM[w]))
        else:
            out.append(w)
    return out


def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _numbers(words: list[str]) -> list[str]:
    return [w for w in words if any(c.isdigit() for c in w)]


def check(answer: str, accepted: list[str], mode: str) -> bool:
    words = norm(answer)
    if not words:
        return False
    joined = " ".join(words)
    for item in accepted:
        t = norm(item)
        if not t:
            continue
        tj = " ".join(t)
        if mode == "exact":
            ok = joined == tj
        elif mode == "key":
            ok = all(w in words for w in t)
        else:
            limit = 0 if len(tj) <= 4 else 1 if len(tj) <= 8 else 2
            # Imlo bardoshliligi sonlarga tegishli emas.
            ok = (_numbers(words) == _numbers(t) and abs(len(joined) - len(tj)) <= limit
                  and lev(joined, tj) <= limit)
        if ok:
            return True
    return False


def grade(key: list[dict], answers: list, accepted: list[int], scores: dict | None = None) -> tuple[list[dict], int]:
    """Har bir savol bo'yicha natija: avtomatik tekshiruv + o'qituvchi qabul qilganlari.

    Yozma ish (max > 0) avtomatik tekshirilmaydi: bali scores ichida bo'ladi.
    """
    review, total = [], 0
    for i, q in enumerate(key):
        mine = answers[i] if i < len(answers) else None
        most = q.get("max") or 0
        if most:
            auto = manual = ok = False
            # Javobsiz yozma ish 0 ball; Speaking ilovadan tashqarida topshiriladi.
            got = (scores or {}).get(str(i))
            if got is None and not (mine or "").strip() and q.get("sec") != "Speaking":
                got = 0
        else:
            got = None
            auto = check(mine or "", q["acc"], q["md"]) if q["w"] else mine == q["a"]
            manual = bool(q["w"] and not auto and i in accepted)
            ok = auto or manual
        total += ok
        review.append({"t": q["t"], "img": q["img"], "opts": q.get("opts", []), "w": q["w"], "a": q["a"],
                       "acc": q["acc"], "my": mine, "auto": auto, "manual": manual, "ok": ok,
                       "label": q.get("label") or str(i + 1), "sec": q.get("sec", ""), "k": q.get("k"),
                       "max": most, "got": got})
    return review, total

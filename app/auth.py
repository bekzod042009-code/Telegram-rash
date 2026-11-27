"""Telegram initData tekshiruvi va rol bo'yicha kirish."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException

from . import config, db

MAX_AGE = 24 * 3600


def verify_init_data(init_data: str, token: str) -> dict | None:
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
        received = data.pop("hash")
        check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected.encode(), received.encode()):
            return None
        if time.time() - int(data["auth_date"]) > MAX_AGE:
            return None
        user = json.loads(data["user"])
        int(user["id"])
        return user
    except (KeyError, ValueError, TypeError):
        return None


async def tg_user(authorization: str = Header(default="")) -> dict:
    if not config.BOT_TOKEN:
        raise HTTPException(503, "Serverda BOT_TOKEN sozlanmagan.")
    scheme, _, init_data = authorization.partition(" ")
    user = verify_init_data(init_data, config.BOT_TOKEN) if scheme == "tma" else None
    if not user:
        raise HTTPException(401, "Sessiya eskirgan. Ilovani Telegramdan qayta oching.")
    return user


async def admin(user: dict = Depends(tg_user)) -> dict:
    if user["id"] not in config.ADMIN_IDS:
        raise HTTPException(403, "Bu boʻlim faqat admin uchun.")
    return user


async def _account(user: dict, role: str):
    row = await db.pool.fetchrow("SELECT * FROM accounts WHERE tg_id = $1 AND role = $2", user["id"], role)
    if not row:
        raise HTTPException(403, "Avval roʻyxatdan oʻting.")
    return row


async def teacher(user: dict = Depends(tg_user)):
    return await _account(user, "t")


async def student(user: dict = Depends(tg_user)):
    return await _account(user, "s")


async def any_account(user: dict = Depends(tg_user), x_role: str = Header(default="")):
    if x_role not in ("t", "s"):
        raise HTTPException(400, "Rol tanlanmagan.")
    return await _account(user, x_role)

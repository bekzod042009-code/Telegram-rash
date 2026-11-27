import json

import asyncpg

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(
  id SERIAL PRIMARY KEY,
  tg_id BIGINT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('t','s')),
  name TEXT NOT NULL,
  cr BIGINT NOT NULL DEFAULT 0 CHECK (cr >= 0),
  bal BIGINT NOT NULL DEFAULT 0 CHECK (bal >= 0),
  earn BIGINT NOT NULL DEFAULT 0 CHECK (earn >= 0),
  ecr BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tg_id, role)
);
CREATE TABLE IF NOT EXISTS settings(
  id INT PRIMARY KEY CHECK (id = 1),
  data JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS tests(
  code TEXT PRIMARY KEY,
  owner_id INT NOT NULL REFERENCES accounts(id),
  title TEXT NOT NULL,
  minutes INT NOT NULL,
  n INT NOT NULL,
  k INT NOT NULL,
  printed BOOLEAN NOT NULL,
  pub BOOLEAN NOT NULL,
  is_open BOOLEAN NOT NULL,
  subj TEXT NOT NULL,
  pay TEXT NOT NULL,
  price BIGINT NOT NULL,
  sold INT NOT NULL DEFAULT 0,
  key JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS images(
  id TEXT PRIMARY KEY,
  owner_id INT NOT NULL REFERENCES accounts(id),
  test_code TEXT REFERENCES tests(code) ON DELETE CASCADE,
  data BYTEA NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS images_pending ON images(owner_id) WHERE test_code IS NULL;
CREATE TABLE IF NOT EXISTS purchases(
  account_id INT NOT NULL REFERENCES accounts(id),
  test_code TEXT NOT NULL REFERENCES tests(code) ON DELETE CASCADE,
  price BIGINT NOT NULL,
  pay TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, test_code)
);
CREATE TABLE IF NOT EXISTS attempts(
  id BIGSERIAL PRIMARY KEY,
  account_id INT NOT NULL REFERENCES accounts(id),
  test_code TEXT NOT NULL REFERENCES tests(code) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_at TIMESTAMPTZ,
  answers JSONB,
  ok INT
);
CREATE INDEX IF NOT EXISTS attempts_account ON attempts(account_id, test_code);
-- O'qituvchi to'g'ri deb qabul qilgan yozma javoblar (savol tartib raqamlari).
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS accepted JSONB NOT NULL DEFAULT '[]';
CREATE TABLE IF NOT EXISTS ratings(
  account_id INT NOT NULL REFERENCES accounts(id),
  test_code TEXT NOT NULL REFERENCES tests(code) ON DELETE CASCADE,
  stars INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
  PRIMARY KEY (account_id, test_code)
);
CREATE TABLE IF NOT EXISTS requests(
  id SERIAL PRIMARY KEY,
  account_id INT NOT NULL REFERENCES accounts(id),
  type TEXT NOT NULL CHECK (type IN ('topup','pack','withdraw')),
  amount BIGINT NOT NULL,
  credits BIGINT NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','done','rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS referrals(
  invitee_tg BIGINT PRIMARY KEY,
  referrer_tg BIGINT NOT NULL,
  rewarded BOOLEAN NOT NULL DEFAULT FALSE
);
"""

pool: asyncpg.Pool | None = None


async def _init_conn(conn):
    await conn.set_type_codec("jsonb", schema="pg_catalog", encoder=lambda v: json.dumps(v, ensure_ascii=False), decoder=json.loads)


async def connect():
    global pool
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL sozlanmagan. Railway'da PostgreSQL qo'shib, o'zgaruvchini ulang.")
    conn = await asyncpg.connect(config.DATABASE_URL)
    try:
        await conn.execute(SCHEMA)
    finally:
        await conn.close()
    pool = await asyncpg.create_pool(config.DATABASE_URL, init=_init_conn, min_size=1, max_size=10)
    await pool.execute(
        "INSERT INTO settings(id, data) VALUES (1, $1) ON CONFLICT (id) DO NOTHING", config.DEFAULT_SETTINGS)


async def close():
    if pool:
        await pool.close()


async def settings(conn=None) -> dict:
    data = await (conn or pool).fetchval("SELECT data FROM settings WHERE id = 1")
    return {**config.DEFAULT_SETTINGS, **(data or {})}

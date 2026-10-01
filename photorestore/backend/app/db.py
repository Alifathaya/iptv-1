"""PostgreSQL: users, token auth, kuota harian, usage log.
Job execution state tetap di Redis (cukup cepat); Postgres menyimpan
akun + pemakaian untuk limit Free/Premium (Phase 7)."""
import hashlib
import os
import secrets

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://fotorestore:fotorestore-dev@localhost:5432/fotorestore")
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "5"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  token_hash CHAR(64) UNIQUE NOT NULL,
  premium BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS usage (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  job_id CHAR(32) NOT NULL,
  mode TEXT NOT NULL,
  seconds REAL NOT NULL DEFAULT 0,
  out_w INTEGER NOT NULL DEFAULT 0,
  out_h INTEGER NOT NULL DEFAULT 0,
  gpu BOOLEAN NOT NULL DEFAULT FALSE,
  api_cost REAL NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_user_day ON usage (user_id, created_at);
"""

_conn = None


def connect():
    global _conn
    if _conn is None or _conn.closed:
        import psycopg2

        _conn = psycopg2.connect(DATABASE_URL)
        _conn.autocommit = True
        with _conn.cursor() as c:
            c.execute(SCHEMA)
    return _conn


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user() -> tuple:
    token = secrets.token_hex(32)  # hanya tampil sekali di respons register
    con = connect()
    with con.cursor() as c:
        c.execute("INSERT INTO users (token_hash) VALUES (%s) RETURNING id", (_h(token),))
        uid = c.fetchone()[0]
    return uid, token


def auth(token: str):
    con = connect()
    with con.cursor() as c:
        c.execute("SELECT id, premium FROM users WHERE token_hash=%s", (_h(token),))
        row = c.fetchone()
    if not row:
        return None
    return {"id": row[0], "premium": row[1]}


def set_premium(user_id: int, premium: bool = True) -> bool:
    con = connect()
    with con.cursor() as c:
        c.execute("UPDATE users SET premium=%s WHERE id=%s", (premium, user_id))
        return c.rowcount == 1


def daily_usage(user_id: int) -> int:
    con = connect()
    with con.cursor() as c:
        c.execute("SELECT COUNT(*) FROM usage WHERE user_id=%s AND created_at > NOW() - INTERVAL '1 day'",
                  (user_id,))
        return c.fetchone()[0]


def quota(user_id: int, premium: bool) -> dict:
    if premium:
        return {"limit": -1, "used": daily_usage(user_id), "remaining": -1}
    used = daily_usage(user_id)
    return {"limit": FREE_DAILY_LIMIT, "used": used, "remaining": max(0, FREE_DAILY_LIMIT - used)}


def log_usage(user_id: int, job_id: str, mode: str, seconds: float,
              out_w: int, out_h: int, gpu: bool, api_cost: float) -> None:
    con = connect()
    with con.cursor() as c:
        c.execute(
            "INSERT INTO usage (user_id, job_id, mode, seconds, out_w, out_h, gpu, api_cost)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (user_id, job_id, mode, seconds, out_w, out_h, gpu, api_cost))

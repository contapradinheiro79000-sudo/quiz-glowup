"""Persistência simples em SQLite (stdlib, zero dependências extras)."""
import sqlite3
import json
import secrets
import time
from pathlib import Path
import config


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              TEXT PRIMARY KEY,
                payment_id      TEXT,
                name            TEXT,
                email           TEXT,
                answers         TEXT,
                diagnosis       TEXT,
                amount          REAL,
                status          TEXT DEFAULT 'pending',
                gateway         TEXT,
                qr_code         TEXT,
                qr_code_base64  TEXT,
                download_token  TEXT,
                delivered       INTEGER DEFAULT 0,
                created_at      REAL,
                updated_at      REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                answers     TEXT,
                created_at  REAL
            )
        """)


def save_lead(answers: dict):
    with _conn() as c:
        c.execute("INSERT INTO leads (answers, created_at) VALUES (?, ?)",
                  (json.dumps(answers, ensure_ascii=False), time.time()))


def create_order(name, email, answers, diagnosis, amount, gateway):
    oid = secrets.token_urlsafe(9)
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _conn() as c:
        c.execute("""
            INSERT INTO orders (id, name, email, answers, diagnosis, amount, status,
                                gateway, download_token, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (oid, name, email, json.dumps(answers, ensure_ascii=False), diagnosis,
              amount, "pending", gateway, token, now, now))
    return oid, token


def attach_payment(order_id, payment_id, qr_code, qr_code_base64):
    with _conn() as c:
        c.execute("""UPDATE orders SET payment_id=?, qr_code=?, qr_code_base64=?, updated_at=?
                     WHERE id=?""",
                  (str(payment_id), qr_code, qr_code_base64, time.time(), order_id))


def set_status(order_id, status):
    with _conn() as c:
        c.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?",
                  (status, time.time(), order_id))


def mark_delivered(order_id):
    with _conn() as c:
        c.execute("UPDATE orders SET delivered=1, updated_at=? WHERE id=?",
                  (time.time(), order_id))


def get_order(order_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_order_by_payment(payment_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM orders WHERE payment_id=?", (str(payment_id),)).fetchone()
        return dict(row) if row else None

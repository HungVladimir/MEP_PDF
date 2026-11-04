"""Lưu trữ SQLite (thư viện chuẩn, không cần cài thêm)."""
import json
import os
import sqlite3
import time

from .config import DATA_DIR, DEFAULT_SETTINGS

DB_PATH = os.path.join(DATA_DIR, "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS workorders(
  id TEXT PRIMARY KEY,
  wo TEXT NOT NULL,
  description TEXT DEFAULT '',
  created_by TEXT, created_by_name TEXT, created_at REAL,
  file_name TEXT, pdf_name TEXT,
  status TEXT DEFAULT 'new',          -- new | running | ok | error | failed
  fail_reason TEXT DEFAULT '',
  error_count INTEGER,
  result_json TEXT, log_json TEXT DEFAULT '[]',
  page_count INTEGER DEFAULT 0,
  review_decision TEXT,               -- approved | rejected | NULL
  review_by TEXT, review_by_name TEXT, review_note TEXT, review_at REAL
);
CREATE INDEX IF NOT EXISTS ix_wo_created ON workorders(created_at);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""


def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        # Server khởi động lại khi đang xử lý -> đánh dấu thất bại để chạy lại
        c.execute("UPDATE workorders SET status='failed', fail_reason='Server khởi động lại khi đang xử lý, hãy bấm Chạy lại' WHERE status='running'")


def _row(r, full=True):
    if r is None:
        return None
    d = dict(r)
    if full:
        d["result"] = json.loads(d["result_json"]) if d.get("result_json") else None
        d["log"] = json.loads(d["log_json"] or "[]")
    d.pop("result_json", None)
    d.pop("log_json", None)
    d["review"] = None
    if d.get("review_decision"):
        d["review"] = {"decision": d["review_decision"], "by": d["review_by"], "by_name": d["review_by_name"],
                       "note": d["review_note"], "at": d["review_at"]}
    return d


def insert_wo(**f):
    f.setdefault("created_at", time.time())
    keys = ",".join(f)
    with conn() as c:
        c.execute(f"INSERT INTO workorders({keys}) VALUES({','.join('?' * len(f))})", list(f.values()))


def update_wo(wo_id, **f):
    if "result" in f:
        f["result_json"] = json.dumps(f.pop("result"), ensure_ascii=False) if f.get("result") is not None else None
    if "log" in f:
        f["log_json"] = json.dumps(f.pop("log"), ensure_ascii=False)
    sets = ",".join(f"{k}=?" for k in f)
    with conn() as c:
        c.execute(f"UPDATE workorders SET {sets} WHERE id=?", [*f.values(), wo_id])


def get_wo(wo_id, full=True):
    with conn() as c:
        return _row(c.execute("SELECT * FROM workorders WHERE id=?", (wo_id,)).fetchone(), full)


def list_wos(status="", q="", limit=500):
    sql, args = "SELECT * FROM workorders WHERE 1=1", []
    if q:
        sql += " AND (wo LIKE ? OR description LIKE ? OR created_by LIKE ? OR created_by_name LIKE ?)"
        args += [f"%{q}%"] * 4
    if status == "review":
        sql += " AND status IN ('ok','error') AND review_decision IS NULL"
    elif status in ("approved", "rejected"):
        sql += " AND review_decision=?"
        args.append(status)
    elif status:
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with conn() as c:
        return [_row(r, full=False) for r in c.execute(sql, args).fetchall()]


def stats():
    with conn() as c:
        g = lambda sql: c.execute(sql).fetchone()[0]
        return {
            "total": g("SELECT COUNT(*) FROM workorders"),
            "review": g("SELECT COUNT(*) FROM workorders WHERE status IN ('ok','error') AND review_decision IS NULL"),
            "error": g("SELECT COUNT(*) FROM workorders WHERE status='error'"),
            "approved": g("SELECT COUNT(*) FROM workorders WHERE review_decision='approved'"),
            "failed": g("SELECT COUNT(*) FROM workorders WHERE status='failed'"),
        }


def delete_wo(wo_id):
    with conn() as c:
        c.execute("DELETE FROM workorders WHERE id=?", (wo_id,))


def get_settings() -> dict:
    with conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key='app'").fetchone()
    s = dict(DEFAULT_SETTINGS)
    if r:
        s.update(json.loads(r["value"]))
    return s


def save_settings(s: dict):
    with conn() as c:
        c.execute("INSERT INTO settings(key,value) VALUES('app',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (json.dumps(s, ensure_ascii=False),))
"""Lightweight persistent registries: conversations, responses, files.

Backed by sqlite (stdlib). Maps OpenAI-side identifiers to Hyperagent threadIds
so multi-turn chats and the Responses API can reuse a single Hyperagent thread.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Optional


class Store:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        c = self._conn
        c.execute("CREATE TABLE IF NOT EXISTS conversations (key TEXT PRIMARY KEY, thread_id TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS responses "
                  "(id TEXT PRIMARY KEY, thread_id TEXT, model TEXT, status TEXT, meta TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS files "
                  "(id TEXT PRIMARY KEY, filename TEXT, bytes INTEGER, purpose TEXT, "
                  "created INTEGER, content BLOB)")
        c.commit()

    # conversations -----------------------------------------------------------
    def get_thread_for_conversation(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute(
                "SELECT thread_id FROM conversations WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def set_conversation_thread(self, key: str, thread_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO conversations(key, thread_id) VALUES(?,?)",
                (key, thread_id))
            self._conn.commit()

    # responses ---------------------------------------------------------------
    def put_response(self, rid: str, thread_id: str, model: str, status: str,
                     meta: Optional[dict] = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses(id, thread_id, model, status, meta) VALUES(?,?,?,?,?)",
                (rid, thread_id, model, status, json.dumps(meta or {})))
            self._conn.commit()

    def get_response(self, rid: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, thread_id, model, status, meta FROM responses WHERE id=?",
                (rid,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "thread_id": row[1], "model": row[2],
                "status": row[3], "meta": json.loads(row[4] or "{}")}

    # files -------------------------------------------------------------------
    def put_file(self, fid: str, filename: str, nbytes: int, purpose: str,
                 created: int = 0, content: Optional[bytes] = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO files(id, filename, bytes, purpose, created, content) "
                "VALUES(?,?,?,?,?,?)", (fid, filename, nbytes, purpose, created, content))
            self._conn.commit()

    def get_file(self, fid: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, filename, bytes, purpose, created FROM files WHERE id=?",
                (fid,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "filename": row[1], "bytes": row[2], "purpose": row[3],
                "created": row[4] or 0}

    def get_file_content(self, fid: str) -> Optional[bytes]:
        with self._lock:
            row = self._conn.execute(
                "SELECT content FROM files WHERE id=?", (fid,)).fetchone()
        return row[0] if row and row[0] is not None else None

    def list_files(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, filename, bytes, purpose, created FROM files "
                "ORDER BY created DESC").fetchall()
        return [{"id": r[0], "filename": r[1], "bytes": r[2], "purpose": r[3],
                 "created": r[4] or 0} for r in rows]

    def delete_file(self, fid: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM files WHERE id=?", (fid,))
            self._conn.commit()
            return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()

"""MySQL access helpers for AdvisorScout.

Connections are opened per call (Dash callbacks run on a thread pool, and
``pymysql`` connections are not safe to share across threads). Helpers always
use parameterized queries via ``DictCursor`` so callers get dict rows.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterable, Sequence

import pymysql
from dotenv import load_dotenv

load_dotenv()

_MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "academicworld"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


def get_connection() -> pymysql.connections.Connection:
    return pymysql.connect(**_MYSQL_CONFIG)


@contextmanager
def cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params or ())
        return list(cur.fetchall())


def execute(sql: str, params: Sequence[Any] | None = None) -> int:
    with cursor() as cur:
        return cur.execute(sql, params or ())


def call_proc(name: str, args: Iterable[Any] = ()) -> list[dict]:
    """Call a stored procedure and return the first result set as dicts."""
    with cursor() as cur:
        cur.callproc(name, list(args))
        try:
            return list(cur.fetchall())
        except pymysql.err.ProgrammingError:
            return []


@contextmanager
def transaction():
    """Yield a cursor wrapped in an explicit transaction (autocommit off)."""
    conn = get_connection()
    conn.autocommit(False)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

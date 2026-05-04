"""Apply MySQL DDL from sql/schema_extensions.sql and create Mongo indexes.

Run from repo root::

    python -m scripts.init_db

Requires ``.env`` with MySQL and Mongo credentials (see ``.env.example``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import pymysql

from mongodb_utils import get_db, publications, reviews
from mysql_utils import get_connection


def _strip_line_comments(sql_text: str) -> str:
    """Remove ``-- ...`` end-of-line comments so semicolons inside them do not split."""
    out_lines: list[str] = []
    for line in sql_text.splitlines():
        idx = line.find("--")
        if idx >= 0:
            line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


def _split_mysql_statements(sql_text: str) -> list[str]:
    """Split on semicolons outside of quoted strings (good enough for our DDL)."""
    sql_text = _strip_line_comments(sql_text)
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    escape = False
    for ch in sql_text:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\" and (in_single or in_double):
            escape = True
            buf.append(ch)
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            continue
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            buf = []
            if stmt:
                parts.append(stmt)
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    out: list[str] = []
    for raw in parts:
        # strip full-line SQL comments
        lines = []
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("--") or not s:
                continue
            lines.append(line)
        stmt = "\n".join(lines).strip()
        if stmt:
            out.append(stmt)
    return out


def apply_mysql_schema() -> None:
    path = ROOT / "sql" / "schema_extensions.sql"
    text = path.read_text(encoding="utf-8")
    statements = _split_mysql_statements(text)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()
    print(f"MySQL: applied {len(statements)} statements from {path.name}")

    # Secondary index (omit from .sql so older MySQL without ``DROP INDEX IF EXISTS`` still works)
    conn2 = get_connection()
    try:
        with conn2.cursor() as cur:
            try:
                cur.execute(
                    "CREATE INDEX idx_fk_keyword_score ON faculty_keyword (keyword_id, score DESC)"
                )
                conn2.commit()
                print("MySQL: created index idx_fk_keyword_score")
            except pymysql.err.OperationalError as exc:
                if exc.args[0] == 1061:  # Duplicate key name
                    print("MySQL: index idx_fk_keyword_score already exists")
                else:
                    raise
    finally:
        conn2.close()


def apply_mongo_indexes() -> None:
    db = get_db()
    pubs = publications()
    pubs.create_index([("id", 1)], unique=False, name="idx_pub_id")
    pubs.create_index(
        [("keywords.name", 1), ("year", -1)],
        name="idx_keywords_name_year",
    )
    print("MongoDB: ensured indexes on publications.id and keywords.name+year")

    coll_name = "faculty_reviews"
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["faculty_id", "user_name", "rating", "text", "created_at"],
            "properties": {
                "faculty_id": {"bsonType": "int"},
                "user_name": {"bsonType": "string"},
                "rating": {"bsonType": "int", "minimum": 1, "maximum": 5},
                "text": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
            },
        }
    }
    existing = db.list_collection_names()
    if coll_name not in existing:
        db.create_collection(coll_name, validator=validator, validationLevel="strict")
        print(f"MongoDB: created collection {coll_name} with JSON schema validator")
    else:
        # coll exists from a previous run — try to update validator (may fail on older Mongo)
        try:
            db.command("collMod", coll_name, validator=validator, validationLevel="strict")
            print(f"MongoDB: updated validator on {coll_name}")
        except Exception as exc:
            print(f"MongoDB: could not collMod {coll_name}: {exc}")
    reviews().create_index([("faculty_id", 1), ("created_at", -1)], name="idx_rev_faculty_time")


def main() -> int:
    try:
        apply_mysql_schema()
    except Exception as exc:
        print(f"MySQL schema apply failed: {exc}")
        return 1
    try:
        apply_mongo_indexes()
    except Exception as exc:
        print(f"Mongo init failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

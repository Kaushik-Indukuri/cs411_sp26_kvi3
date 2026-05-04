"""Standalone connectivity smoke test for the three databases.

Run with ``python -m scripts.health_check`` from the repo root. Useful when
debugging environment / credential issues outside the Dash app.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mongodb_utils import get_db as get_mongo_db
from mysql_utils import query as mysql_query
from neo4j_utils import run_query as neo4j_query


def check_mysql() -> str:
    rows = mysql_query("SELECT COUNT(*) AS n FROM faculty")
    return f"MySQL OK: faculty count = {rows[0]['n']}"


def check_mongo() -> str:
    n = get_mongo_db().publications.count_documents({})
    return f"Mongo OK: publications count = {n}"


def check_neo4j() -> str:
    rows = neo4j_query("MATCH (n:FACULTY) RETURN count(n) AS n")
    return f"Neo4j OK: FACULTY nodes = {rows[0]['n']}"


def main() -> int:
    failures = 0
    for label, check in (("mysql", check_mysql), ("mongo", check_mongo), ("neo4j", check_neo4j)):
        try:
            print(check())
        except Exception as exc:
            failures += 1
            print(f"{label} FAIL: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Neo4j access helpers for AdvisorScout.

The official ``neo4j`` Python driver is thread-safe; one driver instance is
reused for the lifetime of the Dash app. Callers should use ``run_query`` for
reads and ``run_write`` for writes so we exercise the proper transaction
function on each call.
"""

from __future__ import annotations

import atexit
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()

_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "academicworld")


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD))
    atexit.register(driver.close)
    return driver


def run_query(cypher: str, **params: Any) -> list[dict]:
    with get_driver().session(database=_NEO4J_DATABASE) as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


def run_write(cypher: str, **params: Any) -> list[dict]:
    def _tx(tx):
        result = tx.run(cypher, **params)
        return [dict(record) for record in result]

    with get_driver().session(database=_NEO4J_DATABASE) as session:
        return session.execute_write(_tx)

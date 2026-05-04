"""MongoDB access helpers for AdvisorScout.

``MongoClient`` is process-wide and thread-safe, so a single module-level
client is reused for the lifetime of the Dash app.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
_MONGO_DATABASE = os.getenv("MONGO_DATABASE", "academicworld")


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(_MONGO_URI, appname="advisor-scout")


def get_db() -> Database:
    return get_client()[_MONGO_DATABASE]


def publications():
    return get_db()["publications"]


def faculty():
    return get_db()["faculty"]


def reviews():
    """User-supplied faculty reviews collection (created at init time)."""
    return get_db()["faculty_reviews"]

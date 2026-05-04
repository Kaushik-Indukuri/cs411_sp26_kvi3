"""External API helpers (OpenAlex) for extra-credit A2."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import requests

OPENALEX_BASE = "https://api.openalex.org"
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "AdvisorScout/1.0 (CS411 course project; contact: university email)",
        "Accept": "application/json",
    }
)


def _short_openalex_id(url_or_id: str) -> str:
    if not url_or_id:
        return ""
    s = str(url_or_id).rstrip("/")
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    return s


@lru_cache(maxsize=256)
def _author_search_cached(name_key: str) -> list[dict[str, Any]]:
    """Low-volume cache keyed by normalized name (not full affiliation)."""
    r = SESSION.get(
        f"{OPENALEX_BASE}/authors",
        params={"search": name_key, "per_page": 25},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return list(data.get("results") or [])


def find_openalex_author(faculty_name: str, university_hint: str) -> dict[str, Any] | None:
    """Pick the best OpenAlex author record using name + optional university substring match."""
    name_key = re.sub(r"\s+", " ", (faculty_name or "").strip())
    if len(name_key) < 3:
        return None
    results = _author_search_cached(name_key.lower())
    if not results:
        return None
    hint = (university_hint or "").lower()
    scored: list[tuple[float, dict[str, Any]]] = []
    for a in results:
        score = 0.0
        inst = (a.get("last_known_institution") or {}).get("display_name") or ""
        if hint and hint[:4] in inst.lower():
            score += 50.0
        wc = float(a.get("works_count") or 0)
        score += min(wc / 200.0, 10.0)
        an = (a.get("display_name") or "").lower()
        if name_key.split(",")[0].lower().strip() in an:
            score += 5.0
        scored.append((score, a))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1] if scored else None


@lru_cache(maxsize=512)
def fetch_recent_works_for_author(author_openalex_id: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return recent works for an OpenAlex author id (e.g. ``A5078227234``)."""
    aid = _short_openalex_id(author_openalex_id)
    if not aid.startswith("A"):
        aid = f"A{aid}" if aid.isdigit() else aid
    r = SESSION.get(
        f"{OPENALEX_BASE}/works",
        params={
            "filter": f"author.id:{aid}",
            "sort": "publication_year:desc",
            "per_page": min(max(limit, 1), 25),
        },
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    out: list[dict[str, Any]] = []
    for w in data.get("results") or []:
        title = (w.get("display_name") or w.get("title") or "").strip()
        year = w.get("publication_year")
        cited = w.get("cited_by_count")
        wid = _short_openalex_id(w.get("id") or "")
        out.append(
            {
                "openalex_id": wid,
                "title": title or "(untitled)",
                "year": year,
                "cited_by_count": cited,
                "url": w.get("id"),
            }
        )
    return out


def openalex_works_for_faculty(faculty_name: str, university_name: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Resolve author then return (author_meta_or_none, works_rows)."""
    author = find_openalex_author(faculty_name, university_name)
    if not author:
        return None, []
    aid = _short_openalex_id(author.get("id") or "")
    works = fetch_recent_works_for_author(aid, limit=12)
    meta = {
        "openalex_id": aid,
        "display_name": author.get("display_name"),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "last_known_institution": (author.get("last_known_institution") or {}).get("display_name"),
    }
    return meta, works

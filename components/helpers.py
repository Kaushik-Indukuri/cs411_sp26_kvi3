"""Shared helpers for AdvisorScout widgets."""

from __future__ import annotations

from mysql_utils import query


def mysql_id_to_neo4j(mid: int) -> str:
    return f"f{int(mid)}"


def neo4j_id_to_mysql(nid: str) -> int:
    if not nid or not str(nid).startswith("f"):
        raise ValueError(f"Invalid Neo4j faculty id: {nid!r}")
    return int(str(nid)[1:])


def keyword_dropdown_options(rows: list[dict], current_value: str | None) -> list[dict]:
    """Build Dash dropdown options; keep ``current_value`` present so selection is not cleared.

    ``dcc.Dropdown`` clears ``value`` when it is missing from ``options``. After a user picks a
    keyword found via search, ``search_value`` resets and this callback often returns the
    short default list (first 80 names), which omits their choice unless we prepend it here.
    """
    opts = [{"label": r["label"], "value": r["value"]} for r in rows]
    if not current_value:
        return opts
    if any(o.get("value") == current_value for o in opts):
        return opts
    found = query(
        "SELECT name AS label, name AS `value` FROM keyword WHERE name = %s LIMIT 1",
        (current_value,),
    )
    if found:
        head = {"label": found[0]["label"], "value": found[0]["value"]}
    else:
        head = {"label": current_value, "value": current_value}
    return [head, *opts]

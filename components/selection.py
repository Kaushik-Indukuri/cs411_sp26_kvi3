"""Centralized ``selected-faculty`` store updates (W1 table + W5 graph tap).

Only one Dash callback may ``Output`` a given component property; graph taps and
table row picks both funnel through here.
"""

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, callback_context as ctx

from components.helpers import neo4j_id_to_mysql
from components.w1_search import W1_PREFIX
from components.w5_network import W5_PREFIX
from mysql_utils import query


def register_callbacks(app) -> None:
    @app.callback(
        Output("selected-faculty", "data"),
        Input(f"{W1_PREFIX}-table", "selected_rows"),
        Input(f"{W5_PREFIX}-cyto", "tapNodeData"),
        State(f"{W1_PREFIX}-table", "data"),
        prevent_initial_call=True,
    )
    def _faculty_selection(selected_rows, tap_node, table_data):
        tid = ctx.triggered_id

        if tid == f"{W5_PREFIX}-cyto":
            if not tap_node:
                return dash.no_update
            nid = tap_node.get("id")
            if not nid or not str(nid).startswith("f"):
                return dash.no_update
            try:
                mid = neo4j_id_to_mysql(str(nid))
            except ValueError:
                return dash.no_update
            rows = query(
                """
                SELECT f.id AS faculty_id, f.name AS faculty_name, u.name AS university_name
                FROM faculty f
                JOIN university u ON f.university_id = u.id
                WHERE f.id = %s
                LIMIT 1
                """,
                (mid,),
            )
            if rows:
                r = rows[0]
                return {
                    "faculty_id": int(r["faculty_id"]),
                    "faculty_name": r.get("faculty_name"),
                    "university_name": r.get("university_name"),
                }
            return {
                "faculty_id": mid,
                "faculty_name": tap_node.get("label") or str(nid),
                "university_name": "",
            }

        # W1 table
        if not selected_rows or not table_data:
            return None
        idx = selected_rows[0]
        if idx is None or idx >= len(table_data):
            return None
        row = table_data[idx]
        return {
            "faculty_id": int(row["faculty_id"]),
            "faculty_name": row.get("faculty_name"),
            "university_name": row.get("university_name"),
        }

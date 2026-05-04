"""W9 — Mark faculty as contacted (Neo4j MERGE/DELETE on ``DashUser``–``CONTACTED``–``FACULTY``)."""

from __future__ import annotations

from dash import Input, Output, callback, callback_context as ctx, html

from components.helpers import mysql_id_to_neo4j
from neo4j_utils import run_query, run_write

W9_PREFIX = "w9"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W9_PREFIX}-card",
        children=[
            html.H3("Contact tracker"),
            html.Div(
                className="widget-body",
                children=[
                    html.Button("Mark as contacted", id=f"{W9_PREFIX}-mark", n_clicks=0),
                    html.Button("Unmark", id=f"{W9_PREFIX}-unmark", n_clicks=0),
                    html.Div(id=f"{W9_PREFIX}-msg", className="muted"),
                    html.H5("Your contacted faculty", style={"marginTop": "10px"}),
                    html.Div(id=f"{W9_PREFIX}-list"),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W9_PREFIX}-msg", "children"),
        Output(f"{W9_PREFIX}-list", "children"),
        Input(f"{W9_PREFIX}-mark", "n_clicks"),
        Input(f"{W9_PREFIX}-unmark", "n_clicks"),
        Input("user-name-input", "value"),
        Input("selected-faculty", "data"),
        prevent_initial_call=False,
    )
    def _contact(n_mark, n_unmark, user_name: str | None, sel: dict | None):
        user = (user_name or "").strip()
        tid = ctx.triggered_id
        msg = ""

        if tid in (f"{W9_PREFIX}-mark", f"{W9_PREFIX}-unmark"):
            if not user:
                msg = "Enter your name in the header."
            elif not sel or sel.get("faculty_id") is None:
                msg = "Select a faculty in W1."
            else:
                fid_neo = mysql_id_to_neo4j(int(sel["faculty_id"]))
                try:
                    if tid == f"{W9_PREFIX}-mark" and (n_mark or 0) > 0:
                        run_write(
                            """
                            MATCH (f:FACULTY {id: $fid})
                            MERGE (u:DashUser {name: $uname})
                            MERGE (u)-[r:CONTACTED]->(f)
                            ON CREATE SET r.at = datetime()
                            RETURN r.at AS at
                            """,
                            fid=fid_neo,
                            uname=user,
                        )
                        msg = "Marked as contacted."
                    elif tid == f"{W9_PREFIX}-unmark" and (n_unmark or 0) > 0:
                        run_write(
                            """
                            MATCH (:DashUser {name: $uname})-[r:CONTACTED]->(:FACULTY {id: $fid})
                            DELETE r
                            RETURN 1 AS ok
                            """,
                            fid=fid_neo,
                            uname=user,
                        )
                        msg = "Contact edge removed."
                except Exception as exc:
                    msg = f"Neo4j error: {exc}"

        if not user:
            lst = html.Span("—", className="muted")
        else:
            rows = run_query(
                """
                MATCH (u:DashUser {name: $uname})-[r:CONTACTED]->(f:FACULTY)
                RETURN f.id AS id, f.name AS name, r.at AS at
                ORDER BY r.at DESC
                LIMIT 40
                """,
                uname=user,
            )
            if not rows:
                lst = html.P("Nobody marked yet.", className="muted")
            else:
                lst = html.Ul(
                    [
                        html.Li(f"{r.get('name')} ({r.get('id')}) — {r.get('at')}")
                        for r in rows
                    ]
                )
        return msg, lst

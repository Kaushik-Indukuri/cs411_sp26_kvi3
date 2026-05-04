"""W6 — Favorites (MySQL transactional INSERT/DELETE + trigger-maintained popularity)."""

from __future__ import annotations

from dash import Input, Output, callback, callback_context as ctx, html

from mysql_utils import query, transaction

W6_PREFIX = "w6"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W6_PREFIX}-card",
        children=[
            html.H3("Favorites"),
            html.Div(
                className="widget-body",
                children=[
                    html.Button("Toggle favorite for selected faculty", id=f"{W6_PREFIX}-toggle", n_clicks=0),
                    html.Div(id=f"{W6_PREFIX}-msg", className="muted"),
                    html.H5("Your list", style={"marginBottom": "6px"}),
                    html.Div(id=f"{W6_PREFIX}-list"),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W6_PREFIX}-msg", "children"),
        Output(f"{W6_PREFIX}-list", "children"),
        Input(f"{W6_PREFIX}-toggle", "n_clicks"),
        Input("user-name-input", "value"),
        Input("selected-faculty", "data"),
        prevent_initial_call=False,
    )
    def _favorites(_n_clicks, user_name: str | None, sel: dict | None):
        user = (user_name or "").strip()
        tid = ctx.triggered_id
        msg = ""
        if tid == f"{W6_PREFIX}-toggle" and (_n_clicks or 0) > 0:
            if not user:
                msg = "Enter your name in the header first."
            elif not sel or sel.get("faculty_id") is None:
                msg = "Select a faculty in W1 first."
            else:
                fid = int(sel["faculty_id"])
                try:
                    with transaction() as cur:
                        cur.execute(
                            "SELECT id FROM user_favorites WHERE user_name = %s AND faculty_id = %s",
                            (user, fid),
                        )
                        exists = cur.fetchone()
                        if exists:
                            cur.execute(
                                "DELETE FROM user_favorites WHERE user_name = %s AND faculty_id = %s",
                                (user, fid),
                            )
                            msg = "Removed from favorites."
                        else:
                            cur.execute(
                                "INSERT INTO user_favorites (user_name, faculty_id) VALUES (%s, %s)",
                                (user, fid),
                            )
                            msg = "Added to favorites."
                except Exception as exc:
                    msg = f"Error: {exc}"
        return msg, _list_html(user, sel)


def _list_html(user: str, sel: dict | None) -> html.Ul | html.Div:
    if not user:
        return html.Div("—", className="muted")
    rows = query(
        """
        SELECT uf.faculty_id, f.name, uf.added_at
        FROM user_favorites uf
        JOIN faculty f ON f.id = uf.faculty_id
        WHERE uf.user_name = %s
        ORDER BY uf.added_at DESC
        LIMIT 40
        """,
        (user,),
    )
    if not rows:
        return html.P("No favorites yet.", className="muted")
    items = []
    for r in rows:
        mark = " (selected)" if sel and int(sel.get("faculty_id") or -1) == int(r["faculty_id"]) else ""
        items.append(html.Li(f"{r.get('name')} (id {r['faculty_id']}){mark}"))
    return html.Ul(items)

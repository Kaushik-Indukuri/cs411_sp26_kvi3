"""W4 — Faculty profile: MySQL + MongoDB join (extra-credit A1)."""

from __future__ import annotations

from dash import Input, Output, callback, html

from mongodb_utils import faculty as mongo_faculty, publications as mongo_pubs
from mysql_utils import query

W4_PREFIX = "w4"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W4_PREFIX}-card",
        children=[
            html.H3("Faculty profile (multi-database)"),
            html.Div(id=f"{W4_PREFIX}-body", className="widget-body muted", children="Select a faculty row in W1."),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W4_PREFIX}-body", "children"),
        Input("selected-faculty", "data"),
    )
    def _render(sel: dict | None):
        if not sel or sel.get("faculty_id") is None:
            return "Select a faculty row in W1."
        fid = int(sel["faculty_id"])
        mysql_rows = query(
            """
            SELECT f.name, f.position, f.research_interest, f.email, f.photo_url,
                   u.name AS university_name,
                   COALESCE(fp.fav_count, 0) AS favorite_count
            FROM faculty f
            JOIN university u ON f.university_id = u.id
            LEFT JOIN faculty_popularity fp ON fp.faculty_id = f.id
            WHERE f.id = %s
            """,
            (fid,),
        )
        if not mysql_rows:
            return f"No MySQL row for faculty id {fid}."
        m = mysql_rows[0]
        doc = mongo_faculty().find_one({"id": fid}, projection={"publications": 1})
        pub_ids = list(doc.get("publications") or []) if doc else []
        pub_ids = pub_ids[:400]
        top_pubs: list[dict] = []
        if pub_ids:
            top_pubs = list(
                mongo_pubs()
                .find(
                    {"id": {"$in": pub_ids}},
                    projection={"id": 1, "title": 1, "year": 1, "numCitations": 1, "venue": 1},
                )
                .sort("numCitations", -1)
                .limit(8)
            )
        pub_blocks = []
        for p in top_pubs:
            pub_blocks.append(
                html.Li(
                    [
                        html.Strong((p.get("title") or "")[:120]),
                        f" — {p.get('year') or '?'} — citations: {p.get('numCitations') or 0}",
                    ]
                )
            )
        photo = m.get("photo_url")
        img = html.Img(src=photo, style={"maxWidth": "120px", "borderRadius": "8px"}) if photo else None
        return html.Div(
            [
                html.Div(
                    style={"display": "flex", "gap": "16px", "alignItems": "flex-start"},
                    children=[
                        img or html.Span(),
                        html.Div(
                            [
                                html.H4(m.get("name"), style={"margin": "0 0 8px"}),
                                html.P(f"{m.get('position') or ''}", style={"margin": "0"}),
                                html.P(m.get("university_name") or "", className="muted", style={"margin": "4px 0"}),
                                html.P(
                                    f"Saved by {m.get('favorite_count', 0)} applicants",
                                    className="muted",
                                    style={"margin": "8px 0"},
                                ),
                                html.P(m.get("research_interest") or "", style={"margin": "8px 0"}),
                                html.P(m.get("email") or "", className="muted", style={"margin": "0"}),
                            ]
                        ),
                    ],
                ),
                html.H5("Top cited papers (MongoDB)", style={"marginTop": "16px"}),
                html.Ul(pub_blocks) if pub_blocks else html.P("No publication linkage in Mongo for this faculty.", className="muted"),
            ]
        )

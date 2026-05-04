"""W7 — Faculty reviews (MongoDB upsert + aggregation; collection has JSON schema validator)."""

from __future__ import annotations

from datetime import datetime, timezone

import dash
from dash import Input, Output, State, callback, callback_context as ctx, dcc, html

from mongodb_utils import reviews

W7_PREFIX = "w7"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W7_PREFIX}-card",
        children=[
            html.H3("Rate & review"),
            html.Div(
                className="widget-body",
                children=[
                    dcc.Slider(
                        id=f"{W7_PREFIX}-rating",
                        min=1,
                        max=5,
                        step=1,
                        value=5,
                        marks={i: str(i) for i in range(1, 6)},
                    ),
                    dcc.Textarea(
                        id=f"{W7_PREFIX}-text",
                        placeholder="Short review (required)…",
                        style={"width": "100%", "minHeight": "72px"},
                    ),
                    html.Button("Submit review", id=f"{W7_PREFIX}-submit", n_clicks=0),
                    html.Div(id=f"{W7_PREFIX}-msg", className="muted"),
                    html.H5("Summary", style={"marginTop": "12px"}),
                    html.Div(id=f"{W7_PREFIX}-summary"),
                    html.H5("Recent reviews", style={"marginTop": "12px"}),
                    html.Div(id=f"{W7_PREFIX}-recent"),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W7_PREFIX}-msg", "children"),
        Output(f"{W7_PREFIX}-summary", "children"),
        Output(f"{W7_PREFIX}-recent", "children"),
        Input(f"{W7_PREFIX}-submit", "n_clicks"),
        Input("selected-faculty", "data"),
        State(f"{W7_PREFIX}-rating", "value"),
        State(f"{W7_PREFIX}-text", "value"),
        State("user-name-input", "value"),
        prevent_initial_call=False,
    )
    def _reviews(n_clicks, sel, rating, text, user_name: str | None):
        user = (user_name or "").strip()
        tid = ctx.triggered_id
        msg = dash.no_update
        if tid == "selected-faculty":
            msg = ""

        if not sel or sel.get("faculty_id") is None:
            return (
                "",
                html.Span("—", className="muted"),
                html.Span("Select a faculty in W1.", className="muted"),
            )

        fid = int(sel["faculty_id"])
        coll = reviews()

        if tid == f"{W7_PREFIX}-submit" and (n_clicks or 0) > 0:
            if not user:
                msg = "Enter your name in the header."
            elif not (text or "").strip():
                msg = "Review text cannot be empty."
            else:
                doc = {
                    "faculty_id": fid,
                    "user_name": user,
                    "rating": int(rating or 5),
                    "text": (text or "").strip()[:4000],
                    "created_at": datetime.now(timezone.utc),
                }
                try:
                    coll.replace_one(
                        {"faculty_id": fid, "user_name": user},
                        doc,
                        upsert=True,
                    )
                    msg = "Review saved."
                except Exception as exc:
                    msg = f"Mongo error: {exc}"

        pipe = [
            {"$match": {"faculty_id": fid}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "n": {"$sum": 1}}},
        ]
        agg = list(coll.aggregate(pipe))
        if agg:
            summary = html.P(
                f"Average rating {agg[0]['avg']:.2f} over {int(agg[0]['n'])} review(s).",
                className="muted",
                style={"margin": 0},
            )
        else:
            summary = html.P("No reviews yet for this faculty.", className="muted", style={"margin": 0})

        recent_docs = list(coll.find({"faculty_id": fid}).sort("created_at", -1).limit(8))
        if not recent_docs:
            recent = html.Span("No reviews yet.", className="muted")
        else:
            recent = html.Ul(
                [
                    html.Li(
                        f"{d.get('user_name')}: {d.get('rating')}★ — {(d.get('text') or '')[:120]}"
                    )
                    for d in recent_docs
                ]
            )
        return msg, summary, recent

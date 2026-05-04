"""W3 — Publication counts by year for papers tagged with a keyword (MongoDB aggregation)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, dcc, html

from components.helpers import keyword_dropdown_options
from mongodb_utils import publications
from mysql_utils import query

W3_PREFIX = "w3"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W3_PREFIX}-card",
        children=[
            html.H3("Keyword trend over time"),
            html.Div(
                className="widget-body",
                children=[
                    dcc.Dropdown(
                        id=f"{W3_PREFIX}-keyword",
                        options=[],
                        placeholder="Search keywords…",
                        searchable=True,
                        clearable=True,
                    ),
                    html.Div(
                        [
                            html.Label("Year range", className="muted"),
                            dcc.RangeSlider(
                                id=f"{W3_PREFIX}-years",
                                min=1970,
                                max=2025,
                                step=1,
                                value=[1995, 2025],
                                marks={1970: "1970", 2000: "2000", 2025: "2025"},
                                allowCross=False,
                            ),
                        ]
                    ),
                    dcc.Loading(dcc.Graph(id=f"{W3_PREFIX}-chart", figure=px.line(title="Pick a keyword"))),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W3_PREFIX}-keyword", "options"),
        Input(f"{W3_PREFIX}-keyword", "search_value"),
        State(f"{W3_PREFIX}-keyword", "value"),
        prevent_initial_call=False,
    )
    def _kw_options(search_value: str | None, current_kw: str | None):
        if not search_value or len(search_value.strip()) < 2:
            rows = query(
                "SELECT name AS label, name AS `value` FROM keyword WHERE name IS NOT NULL ORDER BY name LIMIT 80"
            )
        else:
            like = f"%{search_value.strip()}%"
            rows = query(
                "SELECT name AS label, name AS `value` FROM keyword WHERE name LIKE %s ORDER BY name LIMIT 80",
                (like,),
            )
        return keyword_dropdown_options(rows, current_kw)

    @app.callback(
        Output(f"{W3_PREFIX}-chart", "figure"),
        Input(f"{W3_PREFIX}-keyword", "value"),
        Input(f"{W3_PREFIX}-years", "value"),
    )
    def _chart(kw: str | None, years: list[int] | None):
        empty = px.line(title="Pick a keyword")
        if not kw:
            return empty
        y0, y1 = (years or [1995, 2025])[0], (years or [1995, 2025])[1]
        coll = publications()
        pipeline = [
            {"$match": {"year": {"$gte": int(y0), "$lte": int(y1)}}},
            {"$unwind": "$keywords"},
            {"$match": {"keywords.name": kw}},
            {"$group": {"_id": "$year", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        rows = list(coll.aggregate(pipeline))
        if not rows:
            return px.line(title=f"No Mongo publications for keyword {kw!r} in year range")
        df = pd.DataFrame([{"year": r["_id"], "count": r["count"]} for r in rows])
        fig = px.line(
            df,
            x="year",
            y="count",
            markers=True,
            title=f"Publications tagged “{kw}” by year",
        )
        fig.update_layout(margin=dict(l=20, r=10, t=40, b=40))
        return fig

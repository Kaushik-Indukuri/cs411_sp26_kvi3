"""W2 — Top universities for a keyword (MySQL aggregation + Plotly bar chart)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, dcc, html

from components.helpers import keyword_dropdown_options
from mysql_utils import query

W2_PREFIX = "w2"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W2_PREFIX}-card",
        children=[
            html.H3("Top universities for a keyword"),
            html.Div(
                className="widget-body",
                children=[
                    dcc.Dropdown(
                        id=f"{W2_PREFIX}-keyword",
                        options=[],
                        placeholder="Search keywords (same as W1)…",
                        searchable=True,
                        clearable=True,
                    ),
                    dcc.Loading(dcc.Graph(id=f"{W2_PREFIX}-chart", figure=px.bar(title="Pick a keyword"))),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W2_PREFIX}-keyword", "options"),
        Input(f"{W2_PREFIX}-keyword", "search_value"),
        State(f"{W2_PREFIX}-keyword", "value"),
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
        Output(f"{W2_PREFIX}-chart", "figure"),
        Input(f"{W2_PREFIX}-keyword", "value"),
    )
    def _chart(kw: str | None):
        empty = px.bar(title="Pick a keyword from the dropdown")
        if not kw:
            return empty
        rows = query(
            """
            SELECT u.name AS university, SUM(fk.score) AS total_score
            FROM faculty_keyword fk
            JOIN keyword k ON fk.keyword_id = k.id
            JOIN faculty f ON fk.faculty_id = f.id
            JOIN university u ON f.university_id = u.id
            WHERE k.name = %s
            GROUP BY u.id, u.name
            ORDER BY total_score DESC
            LIMIT 15
            """,
            (kw,),
        )
        if not rows:
            return px.bar(title=f"No data for keyword {kw!r}")
        df = pd.DataFrame(rows)
        fig = px.bar(
            df,
            x="university",
            y="total_score",
            title=f"Top universities — {kw}",
            labels={"total_score": "Sum of keyword scores", "university": ""},
        )
        fig.update_layout(xaxis_tickangle=-35, margin=dict(l=20, r=10, t=40, b=120))
        return fig

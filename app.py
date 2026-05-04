"""AdvisorScout — Dash dashboard for the CS411 Academic World project."""

from __future__ import annotations

import os

from dash import Dash, dcc, html
from dotenv import load_dotenv

from components import (
    selection,
    w1_search,
    w2_universities,
    w3_trend,
    w4_profile,
    w5_network,
    w6_favorites,
    w7_reviews,
    w8_openalex,
    w9_contacted,
)

load_dotenv()

app = Dash(__name__, title="AdvisorScout", suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="selected-faculty", storage_type="session"),
        html.Div(
            className="app-header",
            children=[
                html.Div(
                    [
                        html.H1("AdvisorScout"),
                        html.Div(
                            "Find PhD advisors using MySQL, MongoDB, Neo4j, and OpenAlex.",
                            className="tagline",
                        ),
                    ]
                ),
                dcc.Input(
                    id="user-name-input",
                    placeholder="Your name (favorites, reviews, contacted list)",
                    type="text",
                    debounce=True,
                    className="header-name-input",
                ),
            ],
        ),
        html.Div(
            className="dashboard-rows",
            children=[
                html.Div(
                    className="dashboard-row dashboard-row-2",
                    children=[w1_search.layout(), w4_profile.layout()],
                ),
                html.Div(
                    className="dashboard-row dashboard-row-full",
                    children=[w5_network.layout()],
                ),
                html.Div(
                    className="dashboard-row dashboard-row-3",
                    children=[
                        w6_favorites.layout(),
                        w7_reviews.layout(),
                        w9_contacted.layout(),
                    ],
                ),
                html.Div(
                    className="dashboard-row dashboard-row-3",
                    children=[
                        w2_universities.layout(),
                        w3_trend.layout(),
                        w8_openalex.layout(),
                    ],
                ),
            ],
        ),
    ],
)

for mod in (
    w1_search,
    w4_profile,
    w5_network,
    w6_favorites,
    w7_reviews,
    w9_contacted,
    w2_universities,
    w3_trend,
    w8_openalex,
    selection,
):
    mod.register_callbacks(app)


if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port)

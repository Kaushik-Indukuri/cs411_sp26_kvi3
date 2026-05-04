"""W1 — Faculty search by keyword + university (MySQL view + stored procedure)."""

from __future__ import annotations

from dash import Input, Output, State, callback, dash_table, dcc, html

from components.helpers import keyword_dropdown_options
from mysql_utils import call_proc, query

W1_PREFIX = "w1"


def layout() -> html.Div:
    unis = query(
        "SELECT id AS value, name AS label FROM university WHERE name IS NOT NULL ORDER BY name"
    )
    uni_options = [{"label": r["label"], "value": r["value"]} for r in unis]
    return html.Div(
        className="widget-card",
        id=f"{W1_PREFIX}-card",
        children=[
            html.H3("Faculty search"),
            html.Div(
                className="widget-body",
                children=[
                    dcc.Dropdown(
                        id=f"{W1_PREFIX}-keyword",
                        options=[],
                        placeholder="Type to search keywords…",
                        searchable=True,
                        clearable=True,
                    ),
                    dcc.Dropdown(
                        id=f"{W1_PREFIX}-university",
                        options=[{"label": "All universities", "value": -1}, *uni_options],
                        value=-1,
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Label("Minimum keyword score", className="muted"),
                            dcc.Slider(
                                id=f"{W1_PREFIX}-min-score",
                                min=0,
                                max=100,
                                step=0.5,
                                value=0,
                                marks=None,
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                        ]
                    ),
                    html.Button("Search", id=f"{W1_PREFIX}-search", n_clicks=0, className="btn-primary"),
                    dcc.Loading(
                        dash_table.DataTable(
                            id=f"{W1_PREFIX}-table",
                            columns=[
                                {"name": "ID", "id": "faculty_id"},
                                {"name": "Name", "id": "faculty_name"},
                                {"name": "Position", "id": "position"},
                                {"name": "University", "id": "university_name"},
                                {"name": "Keyword score", "id": "keyword_score", "type": "numeric", "format": {"specifier": ".2f"}},
                            ],
                            data=[],
                            row_selectable="single",
                            selected_rows=[],
                            page_size=12,
                            style_table={"overflowX": "auto"},
                            style_cell={"textAlign": "left", "padding": "6px", "fontSize": "13px"},
                            style_header={"fontWeight": "600"},
                        ),
                    ),
                    html.Div(id=f"{W1_PREFIX}-hint", className="muted"),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W1_PREFIX}-keyword", "options"),
        Input(f"{W1_PREFIX}-keyword", "search_value"),
        State(f"{W1_PREFIX}-keyword", "value"),
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
                "SELECT name AS label, name AS `value` FROM keyword WHERE name LIKE %s ORDER BY CHAR_LENGTH(name) ASC LIMIT 80",
                (like,),
            )
        return keyword_dropdown_options(rows, current_kw)

    @app.callback(
        Output(f"{W1_PREFIX}-table", "data"),
        Output(f"{W1_PREFIX}-hint", "children"),
        Input(f"{W1_PREFIX}-search", "n_clicks"),
        State(f"{W1_PREFIX}-keyword", "value"),
        State(f"{W1_PREFIX}-university", "value"),
        State(f"{W1_PREFIX}-min-score", "value"),
        prevent_initial_call=True,
    )
    def _run_search(_n, kw, uni_id, min_score):
        if not kw:
            return [], "Pick a keyword first."
        try:
            rows = call_proc(
                "GetTopFacultyForKeyword",
                [kw, int(uni_id) if uni_id is not None else -1, float(min_score or 0), 50],
            )
        except Exception as exc:
            return [], f"Query error: {exc}"
        if not rows:
            return [], "No rows returned — try a lower minimum score or a different keyword."
        return rows, f"Showing {len(rows)} faculty (max 50). Select a row to drive other widgets."

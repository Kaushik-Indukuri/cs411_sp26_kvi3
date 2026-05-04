"""W8 — External recent works via OpenAlex (extra-credit A2)."""

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, html

from external_utils import openalex_works_for_faculty

W8_PREFIX = "w8"


def layout() -> html.Div:
    return html.Div(
        className="widget-card",
        id=f"{W8_PREFIX}-card",
        children=[
            html.H3("External recent papers (OpenAlex)"),
            html.Div(
                className="widget-body",
                children=[
                    html.Button("Fetch from OpenAlex", id=f"{W8_PREFIX}-fetch", n_clicks=0),
                    html.Div(id=f"{W8_PREFIX}-body", className="muted"),
                ],
            ),
        ],
    )


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W8_PREFIX}-body", "children"),
        Input(f"{W8_PREFIX}-fetch", "n_clicks"),
        State("selected-faculty", "data"),
        prevent_initial_call=False,
    )
    def _fetch(n_clicks, sel: dict | None):
        if not sel or sel.get("faculty_id") is None:
            return "Select a faculty in W1, then click fetch."
        if not (n_clicks or 0):
            return "Click “Fetch from OpenAlex” after selecting a faculty."
        name = sel.get("faculty_name") or ""
        uni = sel.get("university_name") or ""
        try:
            meta, works = openalex_works_for_faculty(str(name), str(uni))
        except Exception as exc:
            return f"OpenAlex error: {exc}"
        if not meta:
            return "No OpenAlex author match — try a different faculty or refine spelling."
        rows = html.Table(
            [
                html.Tr([html.Th("Year"), html.Th("Citations"), html.Th("Title")]),
                *[
                    html.Tr(
                        [
                            html.Td(str(w.get("year") or "")),
                            html.Td(str(w.get("cited_by_count") or "")),
                            html.Td(
                                html.A(
                                    (w.get("title") or "")[:100],
                                    href=w.get("url") or "#",
                                    target="_blank",
                                )
                            ),
                        ]
                    )
                    for w in works
                ],
            ],
            style={"width": "100%", "fontSize": "12px", "borderCollapse": "collapse"},
        )
        return html.Div(
            [
                html.P(
                    f"Matched author: {meta.get('display_name')} ({meta.get('openalex_id')}) — "
                    f"works {meta.get('works_count')}, cited_by {meta.get('cited_by_count')}. "
                    f"Institution hint: {meta.get('last_known_institution') or 'n/a'}",
                    className="muted",
                ),
                rows if works else html.P("No works returned for that author id.", className="muted"),
            ]
        )

"""W5 — Co-authorship network (Neo4j + dash-cytoscape, parallel runtime hint)."""

from __future__ import annotations

import dash_cytoscape as cyto
from dash import Input, Output, dcc, html

from components.helpers import mysql_id_to_neo4j
from neo4j_utils import run_query

W5_PREFIX = "w5"

_LAYOUT_1HOP = {
    "name": "cose",
    "fit": True,
    "padding": 60,
    "randomize": True,
    "animate": True,
    "animationDuration": 900,
    "directed": False,
    "avoidOverlap": True,
    "nodeDimensionsIncludeLabels": True,
}

_LAYOUT_2HOP = {
    "name": "cose",
    "fit": True,
    "padding": 60,
    "randomize": True,
    "animate": True,
    "animationDuration": 900,
    "avoidOverlap": True,
    "nodeDimensionsIncludeLabels": True,
}

_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "font-size": "11px",
            "text-wrap": "wrap",
            "text-max-width": "100px",
            "text-valign": "bottom",
            "text-halign": "center",
            "text-margin-y": "6px",
            "color": "#1c1f26",
        },
    },
    {
        # Center node (the selected faculty)
        "selector": "node[isCenter = 1]",
        "style": {
            "background-color": "#1f4f99",
            "width": 26,
            "height": 26,
            "border-width": 2,
            "border-color": "#0d2d5c",
            "font-weight": "bold",
            "font-size": "13px",
        },
    },
    {
        # Direct co-authors (hop 1), also intermediate nodes in 2-hop view
        "selector": "node[hop = 1]",
        "style": {
            "background-color": "#0d9488",
            "width": 18,
            "height": 18,
            "border-width": 1,
            "border-color": "#0f766e",
            "cursor": "pointer",
        },
    },
    {
        # 2-hop-only nodes (co-authors of co-authors, not directly linked to center)
        "selector": "node[hop = 2]",
        "style": {
            "background-color": "#64748b",
            "width": 14,
            "height": 14,
            "border-width": 1,
            "border-color": "#475569",
            "cursor": "pointer",
        },
    },
    {
        "selector": "node:selected",
        "style": {
            "border-width": 4,
            "border-color": "#f59e0b",
            "background-color": "#7c3aed",
        },
    },
    {
        # Edges from center → direct co-author
        "selector": "edge[edgeType = 'direct']",
        "style": {
            "width": "mapData(weight, 1, 30, 1.5, 7)",
            "line-color": "#0d9488",
            "curve-style": "bezier",
            "opacity": 0.7,
        },
    },
    {
        # Edges from direct co-author → 2-hop node
        "selector": "edge[edgeType = 'indirect']",
        "style": {
            "width": 1.2,
            "line-color": "#94a3b8",
            "curve-style": "bezier",
            "opacity": 0.5,
            "line-style": "dashed",
        },
    },
]


def layout() -> html.Div:
    return html.Div(
        className="widget-card widget-card--graph",
        id=f"{W5_PREFIX}-card",
        children=[
            html.H3("Co-authorship network"),
            html.Div(
                className="widget-subtitle",
                style={"marginBottom": "12px", "lineHeight": "1.45"},
                children=[
                    html.Br(),
                    "1 hop = direct co-authors (teal). "
                    "2 hops = co-authors of co-authors (grey), branching off teal nodes. ",
                    html.Br(),
                    "Click a node to load them in W4 / W8. Scroll to zoom, drag to pan.",
                ],
            ),
            html.Div(
                className="widget-body",
                children=[
                    html.Label("Graph distance from selected faculty", className="muted"),
                    dcc.RadioItems(
                        id=f"{W5_PREFIX}-depth",
                        value=1,
                        options=[
                            {"label": "1 hop", "value": 1},
                            {"label": "2 hops", "value": 2},
                        ],
                        inline=True,
                        style={
                            "display": "flex",
                            "gap": "18px",
                            "flexWrap": "wrap",
                            "alignItems": "center",
                            "padding": "2px 0 4px",
                        },
                    ),
                    dcc.Loading(
                        cyto.Cytoscape(
                            id=f"{W5_PREFIX}-cyto",
                            layout=_LAYOUT_1HOP,
                            style={"width": "100%", "height": "560px"},
                            elements=[],
                            zoomingEnabled=True,
                            panningEnabled=True,
                            userZoomingEnabled=True,
                            userPanningEnabled=True,
                            boxSelectionEnabled=False,
                            autounselectify=False,
                            minZoom=0.08,
                            maxZoom=3.0,
                            stylesheet=_STYLESHEET,
                        )
                    ),
                    html.Div(id=f"{W5_PREFIX}-hint", className="muted"),
                ],
            ),
        ],
    )


def _elements_for_depth(center_id: str, center_name: str, depth: int) -> tuple[list[dict], str]:
    """Build cytoscape elements.

    1-hop: center → direct co-authors, edges weighted by shared paper count.
    2-hop: center → c1 (direct) → c2 (indirect). Edges branch correctly:
           c1 nodes sit between center and their own c2 neighbours.
    """

    center_elem = {
        "data": {
            "id": center_id,
            "label": (center_name or center_id)[:48],
            "isCenter": 1,
            "hop": 0,
        }
    }

    if depth == 1:
        cypher = """
CYPHER runtime=parallel
MATCH (f:FACULTY {id: $fid})-[:PUBLISH]->(p:PUBLICATION)<-[:PUBLISH]-(co:FACULTY)
WHERE co <> f
WITH co, count(p) AS shared
RETURN co.id AS id, co.name AS name, shared
ORDER BY shared DESC
LIMIT 40
"""
        rows = run_query(cypher, fid=center_id)

        elems = [center_elem]
        for r in rows:
            cid = r["id"]
            w = min(int(r.get("shared") or 1), 30)
            elems.append({
                "data": {
                    "id": cid,
                    "label": (r.get("name") or cid)[:48],
                    "isCenter": 0,
                    "hop": 1,
                }
            })
            elems.append({
                "data": {
                    "id": f"{center_id}|{cid}",
                    "source": center_id,
                    "target": cid,
                    "weight": w,
                    "edgeType": "direct",
                }
            })

        hint = (
            f"{len(rows)} direct co-authors. "
            "Click any node to load them in W4 / W8."
        )
        return elems, hint

    else:
        # Fetch direct co-authors (c1) first
        cypher_c1 = """
CYPHER runtime=parallel
MATCH (f:FACULTY {id: $fid})-[:PUBLISH]->(p:PUBLICATION)<-[:PUBLISH]-(c1:FACULTY)
WHERE c1 <> f
WITH c1, count(p) AS shared
RETURN c1.id AS id, c1.name AS name, shared
ORDER BY shared DESC
LIMIT 20
"""
        c1_rows = run_query(cypher_c1, fid=center_id)
        c1_ids = [r["id"] for r in c1_rows]

        # For each c1, fetch their co-authors (c2) excluding center and other c1s.
        # Edges will be c1→c2, not center→c2.
        cypher_c2 = """
CYPHER runtime=parallel
MATCH (c1:FACULTY)-[:PUBLISH]->(p:PUBLICATION)<-[:PUBLISH]-(c2:FACULTY)
WHERE c1.id IN $c1ids
  AND c2.id <> $fid
  AND NOT c2.id IN $c1ids
WITH c1, c2, count(p) AS shared
RETURN c1.id AS c1id, c2.id AS c2id, c2.name AS c2name, shared
ORDER BY shared DESC
LIMIT 60
"""
        c2_rows = run_query(cypher_c2, c1ids=c1_ids, fid=center_id)

        elems = [center_elem]
        seen_nodes: set[str] = {center_id}

        # Add c1 nodes + center→c1 edges
        for r in c1_rows:
            cid = r["id"]
            w = min(int(r.get("shared") or 1), 30)
            if cid not in seen_nodes:
                elems.append({
                    "data": {
                        "id": cid,
                        "label": (r.get("name") or cid)[:48],
                        "isCenter": 0,
                        "hop": 1,
                    }
                })
                seen_nodes.add(cid)
            elems.append({
                "data": {
                    "id": f"{center_id}|{cid}",
                    "source": center_id,
                    "target": cid,
                    "weight": w,
                    "edgeType": "direct",
                }
            })

        # Add c2 nodes + c1→c2 edges (branching off c1, NOT off center)
        seen_edges: set[str] = set()
        for r in c2_rows:
            c1id = r["c1id"]
            c2id = r["c2id"]
            if c2id not in seen_nodes:
                elems.append({
                    "data": {
                        "id": c2id,
                        "label": (r.get("c2name") or c2id)[:48],
                        "isCenter": 0,
                        "hop": 2,
                    }
                })
                seen_nodes.add(c2id)
            edge_key = f"{c1id}|{c2id}"
            if edge_key not in seen_edges:
                elems.append({
                    "data": {
                        "id": edge_key,
                        "source": c1id,
                        "target": c2id,
                        "weight": min(int(r.get("shared") or 1), 30),
                        "edgeType": "indirect",
                    }
                })
                seen_edges.add(edge_key)

        n_c1 = len(c1_rows)
        n_c2 = len({r["c2id"] for r in c2_rows})
        hint = (
            f"{n_c1} direct co-authors (teal) + {n_c2} two-hop collaborators (grey). "
            "Grey nodes branch off their teal intermediary, not the center."
        )
        return elems, hint


def register_callbacks(app) -> None:
    @app.callback(
        Output(f"{W5_PREFIX}-cyto", "elements"),
        Output(f"{W5_PREFIX}-cyto", "layout"),
        Output(f"{W5_PREFIX}-hint", "children"),
        Input("selected-faculty", "data"),
        Input(f"{W5_PREFIX}-depth", "value"),
    )
    def _graph(sel: dict | None, depth: int | None):
        if not sel or sel.get("faculty_id") is None:
            return [], _LAYOUT_1HOP, "Select a faculty in W1 (or tap a node here after the graph appears)."
        fid = int(sel["faculty_id"])
        neo_id = mysql_id_to_neo4j(fid)
        name = sel.get("faculty_name") or neo_id
        depth = int(depth or 1)
        layout_cfg = _LAYOUT_1HOP if depth == 1 else _LAYOUT_2HOP
        try:
            elems, hint = _elements_for_depth(neo_id, str(name), depth)
            return elems, {**layout_cfg, "randomize": True}, hint
        except Exception as exc:
            return [], _LAYOUT_1HOP, f"Neo4j error: {exc}"
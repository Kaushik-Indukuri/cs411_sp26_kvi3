# AdvisorScout

**AdvisorScout** is a data dashboard for prospective graduate students to discover faculty advisors using the Academic World dataset across **MySQL**, **MongoDB**, **Neo4j**, plus live **OpenAlex** publication data.

## Purpose

**Scenario:** A student is building a PhD application shortlist: they search by research keyword and university, inspect profiles and co-authorship networks, track favorites and who they have emailed, leave short reviews, and pull recent papers from the open web.

**Target users:** Prospective MS/PhD applicants and research-focused master’s students.

**Objectives:** Combine structured university/faculty/keyword data with publication analytics and a lightweight “application CRM” in one browser dashboard.

## Demo

**Video (R3):** https://mediaspace.illinois.edu/media/t/1_izgq91xc

## Installation

1. **Python 3.11+** (tested on 3.13) and a virtualenv:

   ```bash
   cd cs411_sp26_kvi3
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment:** copy `.env.example` to `.env` and set MySQL, MongoDB, and Neo4j credentials.

3. **Database extensions (MySQL + Mongo):** run once after the base Academic World dump is loaded:

   ```bash
   python -m scripts.init_db
   ```

   This creates `user_favorites`, `faculty_popularity`, the `top_faculty_by_keyword` view, stored procedure `GetTopFacultyForKeyword`, triggers, the secondary index on `faculty_keyword`, Mongo indexes on `publications`, and the `faculty_reviews` collection with a JSON schema validator.

4. **Connectivity check (optional):**

   ```bash
   python -m scripts.health_check
   ```

## Usage

```bash
source .venv/bin/activate
python app.py
```

Open `http://127.0.0.1:8050` (or the port in `DASH_PORT`).

**Flow:** Enter your name in the header → pick a keyword and university in **W1** → click **Search** → select a table row with a professor you are interested in. That selection drives **W4** (profile), **W5** (graph), **W6** (favorites), **W7** (reviews), **W8** (OpenAlex), and **W9** (contacted). Use **W2**/**W3** for keyword-level analytics.

## Design

- **Frontend stack:** The entire UI is a Plotly Dash app. W1, W2, W3, and W7 use dropdowns, sliders, and tables for filtering and review input, while W5 uses `dash-cytoscape` to render the co-author graph and W2/W3 use Plotly charts for keyword analytics.
- **Interaction model:** W1 is the entry point. A user searches for a keyword and university, then selects one faculty row. That selection is stored in `dcc.Store(id="selected-faculty")` and drives the profile, graph, favorites, reviews, OpenAlex, and contacted widgets without reloading the page.
- **Layout:** The page is organized as a four-row CSS grid in `assets/style.css`: row 1 shows the search and profile widgets side by side, row 2 gives the graph its own full-width row, row 3 groups user-tracking actions, and row 4 shows the keyword-level analytics and OpenAlex context.
- **Data sources:** The dashboard combines MySQL for keyword, university, favorites, and profile data; MongoDB for publication/review collections; Neo4j for the relationship graph and contact tracker; and OpenAlex for live recent works.

```text
+----------------------+----------------------+
| W1 Search            | W4 Profile           |
+----------------------+----------------------+
|                W5 Network                   |
+----------------------+----------------------+
| W6 Favorites | W7 Reviews | W9 Contacted    |
+----------------------+----------------------+
| W2 Top Unis  | W3 Trend   | W8 OpenAlex     |
+----------------------+----------------------+
```

## Implementation

- [`app.py`](app.py) is the composition root: it builds the header, the shared `selected-faculty` store, the four dashboard rows, and then registers every widget callback.
- [`components/w1_search.py`](components/w1_search.py) performs the initial faculty search against the MySQL keyword view and stored procedure, then writes the chosen faculty into shared state.
- [`components/w2_universities.py`](components/w2_universities.py) and [`components/w3_trend.py`](components/w3_trend.py) turn keyword selections into bar and trend charts so users can compare universities and publication volume.
- [`components/w4_profile.py`](components/w4_profile.py) merges MySQL faculty metadata with MongoDB publication data to show the selected faculty’s profile and top-cited papers.
- [`components/w5_network.py`](components/w5_network.py) queries Neo4j for 1-hop and 2-hop co-authorship neighborhoods and renders them with Cytoscape so the selected faculty becomes the center of the graph.
- [`components/w6_favorites.py`](components/w6_favorites.py), [`components/w7_reviews.py`](components/w7_reviews.py), and [`components/w9_contacted.py`](components/w9_contacted.py) implement the user-facing tracking tools: favorites are stored transactionally in MySQL, reviews are upserted in MongoDB, and contacted faculty are marked in Neo4j.
- [`components/w8_openalex.py`](components/w8_openalex.py) calls the OpenAlex API using the selected faculty name and university for disambiguation, then shows recent external works.
- [`mysql_utils.py`](mysql_utils.py), [`mongodb_utils.py`](mongodb_utils.py), [`neo4j_utils.py`](neo4j_utils.py), and [`external_utils.py`](external_utils.py) isolate connection details and query helpers so the widgets stay focused on UI logic.
- [`sql/schema_extensions.sql`](sql/schema_extensions.sql) and [`scripts/init_db.py`](scripts/init_db.py) create the project-specific database objects: the keyword view, stored procedure, triggers, indexes, review collection validator, and other schema extensions used by the widgets.

**Neo4j note:** This dataset uses uppercase labels (`FACULTY`, `PUBLICATION`, …) and relationship types such as `PUBLISH`. MySQL `faculty.id` maps to Neo4j `FACULTY.id` strings `f0`, `f1`, …

## Database techniques (R13–R15)

At least three required; this project implements six:

1. **Secondary index** — `idx_fk_keyword_score` on `faculty_keyword(keyword_id, score DESC)` (created by `init_db`; PKs do not count per course spec).
2. **View** — `top_faculty_by_keyword` denormalizes faculty, keyword, university, and score for reuse.
3. **Stored procedure** — `GetTopFacultyForKeyword` parameterizes the ranked faculty query used by **W1**.
4. **Trigger** — `AFTER INSERT` / `AFTER DELETE` on `user_favorites` maintains `faculty_popularity.fav_count` (surfaced in **W4**).
5. **Foreign key + UNIQUE constraint** — `user_favorites.faculty_id` references `faculty(id)` `ON DELETE CASCADE`, plus `UNIQUE(user_name, faculty_id)`. Mongo `faculty_reviews` uses a **JSON schema validator** (1–5 star `rating`).
6. **Transaction** — **W6** favorite toggle runs inside `BEGIN`/`COMMIT` via `mysql_utils.transaction()`.

**Parallel runtime (listed technique #8):** **W5** prefixes Cypher with `CYPHER runtime=parallel` where supported.

## Extra-credit capabilities

- **A1 — Multi-database querying:** **W4** loads MySQL profile + university + `faculty_popularity`, then reads MongoDB `faculty.publications` and joins to the `publications` collection for top-cited papers.
- **A2 — External data sourcing:** **W8** calls the OpenAlex REST API for the selected faculty (name + university disambiguation) and lists recent works with links.

## Contributions

| Member | Tasks | Approx. hours |
|--------|--------|----------------|
| Kaushik Indukuri | Everything: schema, Dash widgets, OpenAlex integration, README, demo | 25 |

---

## Rubric checklist (quick reference)

| ID | How it is satisfied |
|----|---------------------|
| R1 | Code in this repository |
| R2 | This README |
| R3 | Demo link in **Demo** section |
| R4–R5 | Useful applicant workflow; combines static DBs + live OpenAlex |
| R6–R8 | Every widget documents which engine it uses; all three engines used |
| R9 | Nine widgets, each with distinct behavior |
| R10 | **W6** (MySQL), **W7** (Mongo), **W9** (Neo4j) perform writes with visible feedback |
| R11 | Multiple widgets take user input (search, sliders, dropdowns, text, buttons) |
| R12 | `assets/style.css` grid + cards |
| R13–R15 | Six techniques documented above |

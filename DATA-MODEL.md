# DATA-MODEL.md — Schema & Data Flow

<p align="center">
  <img src="./docs/database-schema.svg" alt="DOGFOOD 2026 Relational Data Architecture" width="100%">
</p>

## 1. Relational Entity Schema

The data model maps directly from [`fixtures.json`](file:///c:/Users/heman/Desktop/dogfood/fixtures.json) into a clean, relational SQLite database:

The relational model maps the [`fixtures.json`](fixtures.json) dataset directly into a high-performance SQLite database:

| Table | Purpose | Primary Key | Foreign Keys & Constraints |
| :--- | :--- | :--- | :--- |
| **`events`** | Event metadata & cutoff date | `id` (e.g. `evt_01`) | `submissions_close` (ISO-8601 UTC) |
| **`tracks`** | 8 competition categories | `id` (e.g. `trk_01`) | `event_id` $\to$ `events.id` |
| **`judge_tracks`** | N-to-N track assignment mapping | `(judge_id, track_id)` | `judge_id` $\to$ `users.id`, `track_id` $\to$ `tracks.id` |
| **`users`** | Authentication & RBAC roles | `id` (e.g. `jdg_01`) | Indexed `session_token` (`jdg_a_91bc`, etc.) |
| **`teams`** | 40 participating squads | `id` (e.g. `tm_01`) | `name` |
| **`team_members`** | Squad participant email roster | Composite | `team_id` $\to$ `teams.id` |
| **`projects`** | 41 fixture project submissions | `id` (e.g. `prj_01`) | `team_id` $\to$ `teams.id`, `track_id` $\to$ `tracks.id` |
| **`scores`** | 126 evaluation records | `id` (Autoincrement) | `UNIQUE(judge_id, project_id)`, criteria JSON |
| **`rubric_weights`** | Organizer weighting configuration| `criterion` | Functionality (0.40), Quality (0.35), Innovation (0.25) |
| **`community_votes`**| Duplicate-proof anti-Sybil ballot| `id` (Autoincrement) | `UNIQUE(voter_token)`, IP hash fingerprint |

---

## 2. Ingestion Pipeline (`fixtures.json`)

Ingestion is executed by [`seed.py`](file:///c:/Users/heman/Desktop/dogfood/seed.py):
1. **Event (`events`):** Stores event id, name, and exact `submissions_close` timestamp (`2026-03-01T18:00:00Z`).
2. **Tracks (`tracks`):** 8 distinct tracks loaded with IDs `trk_01` through `trk_08`.
3. **Users & Judges (`users`, `judge_tracks`):**
   - 30 judges ingested.
   - Distinct session tokens assigned, including `jdg_a_91bc` and `jdg_b_44de`.
4. **Teams & Members (`teams`, `team_members`):** 40 teams ingested with member email associations.
5. **Projects (`projects`):** 41 projects ingested with timestamps and repo URLs.
6. **Scores (`scores`):** 126 scoring records containing JSON criteria (`functionality`, `quality`, `innovation`) and comments.

---

## 3. Export Path (`GET /api/export.csv`)

The export route generates a standard comma-separated stream directly from normalized calculations:
- `rank`: Integer overall ranking.
- `project_id`: Unique project ID.
- `title`: Project title.
- `track_name`: Associated track name.
- `reviews_count`: Total judge reviews received.
- `raw_score_avg`: Unweighted or raw criteria average.
- `normalized_score`: Calibrated cross-judge score.

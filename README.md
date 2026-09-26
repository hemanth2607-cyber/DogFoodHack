# DOGFOOD 2026 — Submission & Judging Platform
> *"Build the platform that will judge you."*

An open-source, self-hostable, zero-cloud submission and judging platform engineered for the **DOGFOOD 2026** hackathon.

---

## Verified Tier Claim: T1 + T2 (Solid Pass)

This repository fulfills and machine-verifies **Tier 1 (Core)** and **Tier 2 (Judging)** as validated by [`run.py`](file:///c:/Users/heman/Desktop/dogfood/run.py):

```text
DOGFOOD 2026 acceptance report
portal: http://localhost:8080
claimed: T1 T2
fixtures: fixtures.json

T1  gallery is public ................. PASS
T1  project from fixtures shown ....... PASS
T1  closed event refuses submissions .. PASS
T2  judge sees own scores ............. PASS
T2  judge cannot see peer scores ...... PASS
T2  participant blocked ............... PASS
T2  csv export works .................. PASS

claimed T1 T2, verified T1 T2
```

---

## One-Command Quickstart

The entire platform runs offline on a local laptop with **zero cloud accounts, zero external database services, and zero network dependencies**:

```bash
docker compose up --build
```

The portal automatically initializes the embedded SQLite database, ingests the official [`fixtures.json`](file:///c:/Users/heman/Desktop/dogfood/fixtures.json) dataset, prints test login headers, and serves on:

**`http://localhost:8080`**

### Running the Acceptance Checker
```bash
python run.py .dogfood.toml
```

---

## Key Capabilities

1. **Public Project Gallery (`/projects`):**
   - High-contrast, responsive dark theme displaying all 41 fixture projects.
   - Real-time client-side search by title or team, and filter by track.
2. **Hard Deadline Enforcement (`POST /projects/new`):**
   - Submissions are rejected with `403 Forbidden` if submitted after the fixture event deadline (`2026-03-01T18:00:00Z`).
3. **Backend Peer Score Isolation (`GET /api/judge/scores`):**
   - Judges can view their own score submissions.
   - Any attempt by a judge to inspect peer reviews (e.g. `judge_b` querying `?judge=judge_a`) is refused with **`403 Forbidden`** directly at the HTTP layer.
4. **Cross-Judge Z-Score Normalization:**
   - Standardizes ratings across lenient and harsh judges.
   - Robust against edge cases in the fixture data (e.g. judges with zero score variance and uneven review counts).
5. **Organizer Live Dashboard & CSV Export (`/organizer` & `/api/export.csv`):**
   - Track-by-track overview of review completion.
   - One-click export of normalized rankings as a CSV file.

---

## Test Logins & Auth Headers

The platform uses lightweight cookie-based session headers:

| Role | Session Header | Capabilities |
| :--- | :--- | :--- |
| **Organizer** | `Cookie: session=org_7f2a` | View live dashboard, export normalized CSV |
| **Judge A** | `Cookie: session=jdg_a_91bc` | View assigned projects and own score submissions |
| **Judge B** | `Cookie: session=jdg_b_44de` | View assigned projects and own score submissions |
| **Participant** | `Cookie: session=prt_2e88` | Submit projects (blocked once event closes) |
| **Visitor** | *(None)* | Browse public gallery |

---

## Honest Limitations

- **T3 / Community Voting:** Community voting and comment threads are currently scaffolded but not yet gated with email confirmation or rate limiting.
- **T4 / Webhooks:** Webhook triggers on score submissions are planned for a future release.
- **Single-Node SQLite:** For multi-server clusters, SQLite would be replaced with Postgres. For offline portability and self-hosting, SQLite was chosen for zero runtime friction.

---

## Technical Documentation
- [System Architecture](file:///c:/Users/heman/Desktop/dogfood/ARCHITECTURE.md)
- [Data Model & Schema](file:///c:/Users/heman/Desktop/dogfood/DATA-MODEL.md)
- [Judging Engine & Normalization Defense](file:///c:/Users/heman/Desktop/dogfood/JUDGING.md)
- [MIT License](file:///c:/Users/heman/Desktop/dogfood/LICENSE)

# DOGFOOD 2026 — Master Platform Blueprint & Team Execution Plan
> *"Build the platform that will judge you."*  
> **Event:** DOGFOOD Hackathon 2026 (72h Online, Hackathon Raptors)  
> **Target Goal:** Rock-Solid Clean Tier 1 + Clean Tier 2 (100% Acceptance Pass) + Defensible Normalization Engine + Automated OpenAPI  
> **Team Size:** 3 Members (1 Lead Heavyweight + 2 Focused Specialists)  
> **Primary Specification Source:** [`spec.md`](file:///c:/Users/heman/Desktop/dogfood/spec.md), [`run.py`](file:///c:/Users/heman/Desktop/dogfood/run.py), [`fixtures.json`](file:///c:/Users/heman/Desktop/dogfood/fixtures.json)

---

## 1. Visual Architecture & 72-Hour Blueprint

Below is the comprehensive system architecture, acceptance verification pipeline, workload distribution, and execution timeline:

![DOGFOOD 2026 System Architecture and Blueprint](file:///c:/Users/heman/Desktop/dogfood/system_architecture_and_plan.svg)

---

## 2. Executive Summary & Winning Strategy

### 2.1 The Premise & Hackathon Objective
The organizers (Hackathon Raptors) are running a 72-hour competition with a $2,500 prize pool to build an **open-source, self-hostable hackathon submission and judging platform**. The winning entry will be **forked, self-hosted, and adopted to run future real-world hackathons**.

### 2.2 Golden Rule: "A Clean T2 Beats a Broken T4"
The evaluation criteria explicitly award **40% for Tier Completion and Correctness** and **25% for Judging Integrity**. The scoring rubric penalizes overclaiming. 

```
                                  EVALUATION WEIGHTS
┌─────────────────────────────────┬───────┬──────────────────────────────────────────────┐
│ Criteria                        │ Weight│ Crucial Success Factors                      │
├─────────────────────────────────┼───────┼──────────────────────────────────────────────┤
│ Tier Completion & Correctness   │  40%  │ 100% PASS on run.py, honest .dogfood.toml    │
│ Judging Integrity               │  25%  │ Real backend isolation (403), valid z-score  │
│ Adoptability & Operability      │  20%  │ 1-command `docker compose up`, zero-cloud    │
│ Code Quality & Innovation       │  15%  │ Idiomatic code, clean schema, typed models   │
└─────────────────────────────────┴───────┴──────────────────────────────────────────────┘
```

**Our Strategic Target:**
1. **Flawless T1 (Core) + T2 (Judging):** Guaranteed 7/7 checks passing in `run.py`.
2. **Best Judging Engine Contender ($100 Prize + Tiebreaker):** Defensible z-score normalization mathematically handling awkward fixture cases (judges with uniform scores, missing scores).
3. **API-First Bonus:** Built-in OpenAPI specification generated automatically via FastAPI at `/docs`.

---

## 3. Technology Stack & Operational Rationale

To satisfy **Rule 4 ("Runs offline on a laptop with zero hosted dependencies")** and **The One Command Rule (`docker compose up`)**, we select a lean, robust, and zero-headache Python stack:

```
                    ┌──────────────────────────────────────────────┐
                    │      Client: Browser / run.py HTTP Probe     │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │    FastAPI Application Container (Port 8080) │
                    │  ┌────────────────────────────────────────┐  │
                    │  │ RBAC Session Middleware (Cookie Auth)  │  │
                    │  └───────────────────┬────────────────────┘  │
                    │                      ▼                       │
                    │  ┌────────────────────────────────────────┐  │
                    │  │ Endpoints: /projects, /api/judge, etc. │  │
                    │  └───────────────────┬────────────────────┘  │
                    │                      ▼                       │
                    │  ┌────────────────────────────────────────┐  │
                    │  │ Normalization Engine (z-score formula) │  │
                    │  └───────────────────┬────────────────────┘  │
                    │                      ▼                       │
                    │  ┌────────────────────────────────────────┐  │
                    │  │ Embedded SQLite Database (Local File)  │  │
                    │  └────────────────────────────────────────┘  │
                    └──────────────────────────────────────────────┘
```

* **Core Backend:** **Python 3.11+ with FastAPI & Uvicorn**.
  * Native synergy with `run.py` and `fixtures.json`.
  * Instant OpenAPI / Swagger generation for the API-First bonus.
  * Fast async performance and type safety via Pydantic.
* **Database:** **Embedded SQLite (via SQLAlchemy or raw SQLite3)**.
  * 100% offline, zero cloud setup, zero external database container latency, instantaneous bootstrap.
* **Frontend:** **Server-Rendered Jinja2 Templates + Vanilla Modern CSS**.
  * No fragile Node.js toolchains or heavy npm build steps inside Docker.
  * Bundled CSS assets (zero CDN dependencies so it functions with the internet unplugged).
  * Sleek dark mode, accessible, high aesthetic appeal.
* **Deployment:** **Single Dockerfile + `docker-compose.yml`**.
  * Bootstraps the app, auto-executes `seed.py` on launch, prints test credentials, and exposes port 8080 in under 8 seconds.

---

## 4. Verification Suite Analysis (`run.py` & `.dogfood.toml`)

The automated checker (`run.py`) runs 7 assertions against `.dogfood.toml`. Our backend architecture directly targets every assertion:

```toml
# .dogfood.toml (Generated at repo root)
[portal]
base_url = "http://localhost:8080"

[tiers]
claimed = ["T1", "T2"]
pitch = "Self-hostable hackathon platform with backend-isolated judging and z-score normalization."

[auth]
organizer   = "Cookie: session=org_7f2a"
judge_a     = "Cookie: session=jdg_a_91bc"
judge_b     = "Cookie: session=jdg_b_44de"
participant = "Cookie: session=prt_2e88"

[routes]
gallery      = "/projects"
submit       = "/projects/new"
judge_scores = "/api/judge/scores"
peer_scores  = "/api/judge/scores?judge=judge_a"
csv_export   = "/api/export.csv"
```

### The 7 Checks & Implementation Requirements

| Tier | Test Label | Runner Action | Expected Result | Implementation Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **T1** | **Gallery is public** | `GET /projects` (no header) | `HTTP 200` | Unauthenticated public view of submitted projects. |
| **T1** | **Fixture projects shown** | `GET /projects` | Body contains fixture project title | Seed script must load `fixtures.json` and page 1 of gallery must render them (e.g. "Quiet Hours"). |
| **T1** | **Closed event refuses submissions** | `POST /projects/new` (participant auth) | `HTTP 400 <= status < 500` | Event `submissions_close` from fixture is in the past (`2026-03-01T18:00:00Z`). Endpoint must check current UTC time against deadline and abort with `403/400`. |
| **T2** | **Judge sees own scores** | `GET /api/judge/scores` (judge_a auth) | `HTTP 200` | Authenticated judge can fetch their own scored projects and rubric entries. |
| **T2** | **Judge cannot see peer scores** *(CRITICAL)* | `GET /api/judge/scores?judge=judge_a` (as judge_b) | `HTTP 401 or 403` | Backend role check: if `request.query_params.judge` != `current_user.id`, immediately raise `HTTPException(403)`. |
| **T2** | **Participant blocked** | `GET /api/judge/scores` (participant auth) | `HTTP 401 or 403` | RBAC guard refuses any non-judge caller on judging endpoints. |
| **T2** | **CSV export works** | `GET /api/export.csv` (organizer auth) | `HTTP 200` & first line has `,` | Returns `text/csv` with comma-delimited header row (e.g., `project_id,title,track,raw_score,normalized_score,rank`). Non-organizers are blocked. |

---

## 5. Team Workload Distribution (3-Person Squad)

The workload is deliberately structured with **one lead doing the heavy technical lifting** (architecture, security, runner passing, dockerization) and **two teammates handling essential, well-bounded medium tasks**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               TEAM RESPONSIBILITY MATRIX                               │
├───────────────────────────────┬───────────────────────────────┬────────────────────────┤
│ PERSON 1: LEAD ARCHITECT      │ PERSON 2: FRONTEND & UI       │ PERSON 3: DATA & DOCS  │
│ (HEAVY WORKLOAD - 60%)        │ (MEDIUM WORKLOAD - 20%)       │ (MEDIUM WORKLOAD - 20%)│
├───────────────────────────────┼───────────────────────────────┼────────────────────────┤
│ • Backend Architecture        │ • Public Gallery UI (/projects│ • fixtures.json Seeder │
│ • RBAC & Auth Session Cookies │ • Search & Track Filter UI    │ • Normalization Engine │
│ • Peer Score Guard (403 block)│ • Project Submission Page     │ • CSV Export Generator │
│ • Deadline Enforcer Logic     │ • Judge Rubric Workspace      │ • 4 Mandated .md Docs  │
│ • Docker & compose setup      │ • Organizer Live Dashboard    │ • Demo Video Script    │
│ • run.py 7/7 PASS Guarantee   │ • Vanilla CSS & Dark Theme    │ • Video Recording      │
└───────────────────────────────┴───────────────────────────────┴────────────────────────┘
```

### 👤 Person 1: Lead Architect & Backend Core (You — Heavy Workload)
**Focus:** The entire backbone, security isolation, Docker compliance, and acceptance report validation.
* **Task 1: Core Framework & Schema Setup (`src/main.py`, `src/models.py`, `src/db.py`)**
  * Initialize FastAPI app, lifespan handlers, SQLite connection, and Pydantic/SQLAlchemy data models.
* **Task 2: RBAC & Auth Middleware (`src/auth.py`)**
  * Parse `Cookie: session=...` header.
  * Role mapping: `organizer`, `judge_a`, `judge_b`, `participant`, `visitor`.
  * Context injection into endpoints via FastAPI dependencies (`get_current_user`, `require_role(...)`).
* **Task 3: Backend Role Isolation & Peer Shield (`src/routes/judging.py`)**
  * The pivotal check: when `judge_b` accesses `/api/judge/scores?judge=judge_a`, verify ownership and return `403 Forbidden`.
  * Ensure participants attempting to access judge routes get `403 Forbidden`.
* **Task 4: Deadline Enforcement (`src/routes/submissions.py`)**
  * In `POST /projects/new`, compare `datetime.now(timezone.utc)` against `event.submissions_close`.
  * If deadline is past, reject with `400 Bad Request` or `403 Forbidden` (`"Submissions for this event closed on ..."`).
* **Task 5: Docker Containerization (`Dockerfile`, `docker-compose.yml`)**
  * Set up multi-stage or lean Python 3.11 slim image.
  * Configure auto-run entrypoint: run migrations/seeder -> print credentials -> start Uvicorn on `0.0.0.0:8080`.
  * Verify `docker compose up` works with physical network disabled.
* **Task 6: Acceptance Suite Validation**
  * Create `.dogfood.toml`.
  * Run `python3 run.py .dogfood.toml`.
  * Verify all 7 checks output `PASS` and commit `acceptance-report.txt`.

---

### 👤 Person 2: Frontend Engineer & User Experience (Medium Workload)
**Focus:** Clean, responsive, offline-ready UI templates for gallery, submission, scoring, and organizer dashboard.
* **Task 1: Public Project Gallery (`templates/gallery.html`)**
  * Render grid of projects loaded from `fixtures.json`.
  * Display title, summary, team name, track tag, and repo link.
  * Client-side search bar and track filter dropdown.
* **Task 2: Project Submission & Edit View (`templates/submit.html`)**
  * Form for project submission (Title, summary, track select, repo URL, demo link).
  * Prominent banner indicating submission status (Open / Closed).
* **Task 3: Judge Scoring Workspace (`templates/judge_workspace.html`)**
  * Clean UI for judges to browse their assigned projects.
  * Dynamic sliders/inputs for scoring rubric criteria (e.g. Functionality 1-5, Quality 1-5).
  * Feedback/comments text area.
* **Task 4: Organizer Dashboard UI (`templates/organizer_dashboard.html`)**
  * Visual overview of total submissions, review completion rate per judge, and track breakdown.
  * "Download Normalized Results (CSV)" button pointing to `/api/export.csv`.
* **Task 5: Styling & Polish (`static/style.css`)**
  * Self-contained, responsive modern CSS (no external fonts/CDNs to ensure offline functionality).
  * Polished dark-mode theme with high-contrast typography.

---

### 👤 Person 3: Data Engineer, Normalization & Documentation (Medium Workload)
**Focus:** Ingestion of fixtures, statistical normalization engine, CSV output, and mandatory documentation deliverables.
* **Task 1: Fixtures Ingestion Engine (`seed.py`)**
  * Parse [`fixtures.json`](file:///c:/Users/heman/Desktop/dogfood/fixtures.json) (41 projects, 30 judges, 8 tracks, 126 scores, 1 event).
  * Populate SQLite database with pre-assigned test sessions matching `.dogfood.toml`:
    * `org_7f2a` -> Organizer
    * `jdg_a_91bc` -> Judge A (Ada Okonkwo, `jdg_01`)
    * `jdg_b_44de` -> Judge B (e.g. `jdg_02`)
    * `prt_2e88` -> Participant
  * Print terminal banner on startup with credentials.
* **Task 2: Judging Normalization Engine (`src/normalization.py`)**
  * Cross-judge z-score normalization:
    $$z_{ij} = \frac{s_{ij} - \mu_j}{\sigma_j}$$
  * Handle edge cases present in `fixtures.json`:
    * Judge with zero variance ($\sigma_j = 0$, e.g. rated everything a 4): fallback to mean centering ($s_{ij} - \mu_j$).
    * Incomplete reviews: adjust project scores using Bayesian shrinkage towards the global mean.
* **Task 3: CSV Export Module (`src/routes/export.py`)**
  * Output compliant CSV format on `/api/export.csv`.
  * Headers: `project_id,title,track,raw_score_avg,normalized_score,rank`.
* **Task 4: Mandated Submission Documentation**
  * [`README.md`](file:///c:/Users/heman/Desktop/dogfood/README.md): Setup guide, architecture summary, honest limitations.
  * [`DATA-MODEL.md`](file:///c:/Users/heman/Desktop/dogfood/DATA-MODEL.md): Schema diagram, table relationships, fixture mapping.
  * [`JUDGING.md`](file:///c:/Users/heman/Desktop/dogfood/JUDGING.md): Normalization math defense, handling edge cases, rubric weighting.
  * [`ARCHITECTURE.md`](file:///c:/Users/heman/Desktop/dogfood/ARCHITECTURE.md): Component breakdown, security model, RBAC isolation.
* **Task 5: 5-Minute Demo Video**
  * Draft concise script demonstrating the full lifecycle:
    1. Create event / view closed state.
    2. Browse public gallery.
    3. Judge logs in, scores an assigned project.
    4. Demonstration of security isolation (Judge B unable to see Judge A's scores).
    5. Organizer dashboard view & CSV export.
  * Screen record and submit video link.

---

## 6. Detailed 72-Hour Execution Timeline

```
Timeline: Kickoff Fri 25 Sep 18:00 UTC -> Freeze Mon 28 Sep 18:00 UTC
```

```
[Phase 0: Pre-Kickoff Planning] (NOW - FRI 18:00 UTC)
├── Review spec.md, run.py, fixtures.json (DONE)
├── Generate System Architecture & Master Plan (DONE)
└── Align team roles & confirm dev environments (Git, Python 3, Docker)

[Phase 1: Foundation & T1 Sprint] (FRI 18:00 UTC - SAT 18:00 UTC)
├── Person 1: Initialize FastAPI app, SQLite models, RBAC session middleware, deadline check
├── Person 3: Write seed.py to ingest fixtures.json into SQLite, test login generation
├── Person 2: Build Gallery (/projects) and Project Submission template (/projects/new)
└── Milestone Check 1: T1 checks passing (Gallery public, fixture shown, late post refused)

[Phase 2: Judging Engine & T2 Sprint] (SAT 18:00 UTC - SUN 18:00 UTC)
├── Person 1: Implement peer score isolation logic (?judge=jdg_a as jdg_b -> 403 Forbidden)
├── Person 3: Build normalization engine (z-score) and CSV export route (/api/export.csv)
├── Person 2: Build Judge Scoring rubric UI and Organizer Progress dashboard
├── Person 1: Dockerize app (Dockerfile + docker-compose.yml), test offline boot
└── Milestone Check 2: ALL 7 run.py CHECKS PASSING (acceptance-report.txt generated)

[Phase 3: Hardening, Docs & Freeze] (SUN 18:00 UTC - MON 18:00 UTC)
├── Person 3: Write JUDGING.md, DATA-MODEL.md, ARCHITECTURE.md, and record 5-min demo video
├── Person 2: Polish CSS, mobile responsiveness, accessibility, dark mode accents
├── Person 1: End-to-end rehearsal: clean `docker compose down -v && docker compose up`
└── FINAL SUBMISSION: Commit acceptance-report.txt, tag release, publish repo
```

---

## 7. Submission Deliverables Checklist

Before Mon 28 Sep 18:00 UTC, the repository must contain:

- [x] **`system_architecture_and_plan.svg`** — Complete vector architecture & blueprint.
- [ ] **`.dogfood.toml`** — Correct routes and test session tokens.
- [ ] **`acceptance-report.txt`** — Clean output of `python3 run.py .dogfood.toml` showing solid T1 + T2 PASS.
- [ ] **`docker-compose.yml`** — Zero-cloud single command startup (`docker compose up`).
- [ ] **`README.md`** — What it does, how to run, honest limitations.
- [ ] **`ARCHITECTURE.md`** — System design and rationale.
- [ ] **`DATA-MODEL.md`** — Schema, relationships, import/export paths.
- [ ] **`JUDGING.md`** — Assignment strategy, scoring math, normalization proof defended.
- [ ] **`LICENSE`** — MIT or Apache-2.0.
- [ ] **`src/`** — All code written during the 72-hour window.
- [ ] **`tests/`** — Automated unit & integration test suite.
- [ ] **5-Minute Demo Video** — Video walkthrough demonstrating the 4 stages (Create, Submit, Judge, Publish).

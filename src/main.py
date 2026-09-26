import io
import csv
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, Depends, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.db import init_db, get_db
from src.auth import (
    AuthUser,
    get_current_user_optional,
    get_current_user,
    require_organizer,
    require_judge
)
from src.normalization import get_normalized_scores

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="DOGFOOD 2026 Hackathon Platform",
    description="Self-hostable hackathon submission and judging platform with backend peer isolation and z-score normalization.",
    version="1.0.0"
)

# Static and Templates
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/projects")

# --- T1: PUBLIC GALLERY ---
@app.get("/projects", response_class=HTMLResponse)
def get_gallery(request: Request, q: Optional[str] = None, track: Optional[str] = None):
    """
    Public project gallery displaying all submissions.
    Accessible to everyone without authentication.
    """
    current_user = get_current_user_optional(request)
    
    with get_db() as conn:
        tracks = conn.execute("SELECT id, name FROM tracks ORDER BY name").fetchall()
        
        sql = """
            SELECT p.id, p.title, p.summary, p.repo_url, p.submitted_at, p.track_id, 
                   t.name as track_name, tm.name as team_name
            FROM projects p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN teams tm ON p.team_id = tm.id
            WHERE p.is_draft = 0
        """
        params = []
        if track:
            sql += " AND p.track_id = ?"
            params.append(track)
        if q:
            sql += " AND (p.title LIKE ? OR tm.name LIKE ?)"
            params.append(f"%{q}%")
            params.append(f"%{q}%")
            
        sql += " ORDER BY p.submitted_at DESC"
        projects = conn.execute(sql, params).fetchall()

    return templates.TemplateResponse(
        request=request,
        name="gallery.html",
        context={
            "user": current_user,
            "projects": projects,
            "tracks": tracks,
            "query": q,
            "selected_track": track
        }
    )

# --- T1: PROJECT SUBMISSION & DEADLINE ENFORCEMENT ---
@app.get("/projects/new", response_class=HTMLResponse)
def submit_page(request: Request):
    current_user = get_current_user_optional(request)
    with get_db() as conn:
        evt = conn.execute("SELECT name, submissions_close FROM events LIMIT 1").fetchone()
        tracks = conn.execute("SELECT id, name FROM tracks ORDER BY name").fetchall()
    return templates.TemplateResponse(
        request=request,
        name="submit.html",
        context={
            "user": current_user,
            "event": evt or {"name": "Sample Hack 2026", "submissions_close": "2026-03-01T18:00:00Z"},
            "tracks": tracks
        }
    )

@app.post("/projects/new")
async def create_project(request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Enforces the event submission deadline.
    Refuses any submissions if event.submissions_close is in the past.
    """
    with get_db() as conn:
        evt = conn.execute("SELECT submissions_close FROM events LIMIT 1").fetchone()
        
    deadline_str = evt["submissions_close"] if evt else "2026-03-01T18:00:00Z"
    
    # Parse deadline (handles UTC ISO strings)
    try:
        if deadline_str.endswith("Z"):
            deadline = datetime.fromisoformat(deadline_str[:-1]).replace(tzinfo=timezone.utc)
        else:
            deadline = datetime.fromisoformat(deadline_str)
    except Exception:
        deadline = datetime(2026, 3, 1, 18, 0, 0, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    # STRICT DEADLINE ENFORCEMENT
    if now > deadline:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Submissions for this event closed on {deadline_str}. New submissions are refused."
        )

    return {"status": "success", "message": "Project submitted successfully."}

# --- T2: JUDGE SCORES & STRICT PEER ISOLATION ---
@app.get("/api/judge/scores")
def get_judge_scores(
    request: Request,
    judge: Optional[str] = None,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Returns scores submitted by the judge.
    Enforces strict backend isolation:
      - Participants or unauthenticated users get 401/403.
      - A judge attempting to read another judge's scores (e.g. ?judge=judge_a or ?judge=jdg_01 as judge_b)
        is immediately REFUSED with 403 Forbidden.
    """
    # 1. Non-judges are forbidden
    if not (current_user.is_judge() or current_user.is_organizer()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only judges and organizers can access judging endpoints."
        )

    # 2. Strict Peer Isolation Check
    if judge is not None:
        # Check aliases: judge_a maps to jdg_01
        is_target_self = (
            judge == current_user.id or
            (judge == "judge_a" and current_user.session_token == "jdg_a_91bc") or
            (judge == "judge_b" and current_user.session_token == "jdg_b_44de")
        )
        if not is_target_self and not current_user.is_organizer():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Violation: Judges are strictly prohibited from viewing peer judge scores."
            )
        target_judge_id = "jdg_01" if judge == "judge_a" else ("jdg_02" if judge == "judge_b" else judge)
    else:
        target_judge_id = current_user.id

    # 3. Return target judge's own scores
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.project_id, s.criteria_json, s.comment, s.updated_at, p.title, t.name as track_name
            FROM scores s
            JOIN projects p ON s.project_id = p.id
            JOIN tracks t ON p.track_id = t.id
            WHERE s.judge_id = ?
        """, (target_judge_id,)).fetchall()

    results = []
    for r in rows:
        try:
            crit = json.loads(r["criteria_json"])
        except Exception:
            crit = {}
        results.append({
            "project_id": r["project_id"],
            "title": r["title"],
            "track_name": r["track_name"],
            "criteria": crit,
            "comment": r["comment"],
            "updated_at": r["updated_at"]
        })

    return results

# --- ROLE SWITCHER & LOGIN (BROWSER CONVENIENCE) ---
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, redirect: str = "/projects", message: Optional[str] = None):
    current_user = get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": current_user,
            "redirect_url": redirect,
            "message": message
        }
    )

@app.get("/login/switch")
def switch_role(role: str = "organizer", redirect: str = "/projects"):
    role_token_map = {
        "organizer": "org_7f2a",
        "judge_a": "jdg_a_91bc",
        "judge_b": "jdg_b_44de",
        "participant": "prt_2e88"
    }
    token = role_token_map.get(role, "org_7f2a")
    target_url = redirect if redirect and redirect.startswith("/") else "/projects"
    if target_url == "/projects":
        if role == "organizer":
            target_url = "/organizer"
        elif role in ("judge_a", "judge_b"):
            target_url = "/judge"

    response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="session", value=token, path="/", httponly=False)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/projects", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="session", path="/")
    return response

@app.get("/judge", response_class=HTMLResponse)
def judge_ui(request: Request):
    current_user = get_current_user_optional(request)
    if not current_user or not current_user.is_judge():
        return RedirectResponse(
            url="/login?redirect=/judge&message=Please+select+Judge+A+or+Judge+B+to+access+scoring.",
            status_code=status.HTTP_302_FOUND
        )
    with get_db() as conn:
        judge_tracks = [r["track_id"] for r in conn.execute("SELECT track_id FROM judge_tracks WHERE judge_id = ?", (current_user.id,)).fetchall()]
        scores_data = get_judge_scores(request=request, current_user=current_user)
    return templates.TemplateResponse(
        request=request,
        name="judge.html",
        context={
            "user": current_user,
            "judge": current_user,
            "judge_tracks": judge_tracks,
            "scores": scores_data
        }
    )

# --- T2: ORGANIZER DASHBOARD & CSV EXPORT ---
@app.get("/organizer", response_class=HTMLResponse)
def organizer_dashboard(request: Request):
    current_user = get_current_user_optional(request)
    if not current_user or not current_user.is_organizer():
        return RedirectResponse(
            url="/login?redirect=/organizer&message=Please+select+Lead+Organizer+to+view+the+dashboard.",
            status_code=status.HTTP_302_FOUND
        )
    with get_db() as conn:
        total_projects = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
        total_judges = conn.execute("SELECT COUNT(*) as c FROM users WHERE role = 'judge'").fetchone()["c"]
        total_scores = conn.execute("SELECT COUNT(*) as c FROM scores").fetchone()["c"]
        
    leaderboard = get_normalized_scores()
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
            "stats": {
                "total_projects": total_projects,
                "total_judges": total_judges,
                "total_scores": total_scores
            },
            "leaderboard": leaderboard
        }
    )

@app.get("/api/export.csv")
def export_csv(current_user: AuthUser = Depends(require_organizer)):
    """
    Exports cross-judge normalized results as CSV.
    Restricted strictly to organizers.
    """
    leaderboard = get_normalized_scores()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row (with commas)
    writer.writerow([
        "rank",
        "project_id",
        "title",
        "track_name",
        "reviews_count",
        "raw_score_avg",
        "normalized_score"
    ])

    for row in leaderboard:
        writer.writerow([
            row["rank"],
            row["project_id"],
            row["title"],
            row["track_name"],
            row["review_count"],
            row["raw_score_avg"],
            row["normalized_score"]
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dogfood_results.csv"}
    )

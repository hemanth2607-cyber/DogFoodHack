import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.normalization import get_normalized_scores

client = TestClient(app)

def test_public_gallery():
    res = client.get("/projects")
    assert res.status_code == 200
    assert "Glass Signal" in res.text

def test_closed_event_refuses_submission():
    res = client.post(
        "/projects/new",
        headers={"Cookie": "session=prt_2e88"},
        json={"title": "Test Probe", "summary": "Probe"}
    )
    assert 400 <= res.status_code < 500

def test_judge_sees_own_scores():
    res = client.get("/api/judge/scores", headers={"Cookie": "session=jdg_a_91bc"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_peer_isolation_refuses_judge_b():
    # Judge B querying Judge A's scores must be refused with 403
    res = client.get("/api/judge/scores?judge=judge_a", headers={"Cookie": "session=jdg_b_44de"})
    assert res.status_code in (401, 403)

def test_participant_blocked_from_judge_scores():
    res = client.get("/api/judge/scores", headers={"Cookie": "session=prt_2e88"})
    assert res.status_code in (401, 403)

def test_organizer_csv_export():
    res = client.get("/api/export.csv", headers={"Cookie": "session=org_7f2a"})
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    first_line = res.text.splitlines()[0]
    assert "," in first_line

def test_normalization_engine():
    leaderboard = get_normalized_scores()
    assert len(leaderboard) > 0
    top = leaderboard[0]
    assert "normalized_score" in top
    assert 1.0 <= top["normalized_score"] <= 5.0

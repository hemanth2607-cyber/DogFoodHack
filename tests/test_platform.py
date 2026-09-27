import pytest
import uuid
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

def test_judge_submit_score():
    res = client.post(
        "/api/judge/scores",
        headers={"Cookie": "session=jdg_a_91bc"},
        json={
            "project_id": "prj_01",
            "functionality": 4.5,
            "quality": 4.0,
            "innovation": 4.8,
            "comment": "Outstanding offline architecture."
        }
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_participant_blocked_from_submitting_score():
    res = client.post(
        "/api/judge/scores",
        headers={"Cookie": "session=prt_2e88"},
        json={
            "project_id": "prj_01",
            "functionality": 4.5,
            "quality": 4.0,
            "innovation": 4.8
        }
    )
    assert res.status_code in (401, 403)

def test_ai_rubric_copilot():
    res = client.get(
        "/api/judge/ai-suggest?project_id=prj_01",
        headers={"Cookie": "session=jdg_a_91bc"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "suggested_criteria" in data
    assert 1.0 <= data["suggested_criteria"]["functionality"] <= 5.0

# --- NEW TESTS FOR AUDIT, DETAILS, AND DUPLICATE-PROOF VOTING ---

def test_project_details_api():
    res = client.get("/api/projects/prj_01")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "prj_01"
    assert "title" in data
    assert "track_name" in data
    assert "team_name" in data
    assert "community_votes" in data

def test_community_voting_strict_duplicate_prevention():
    test_voter_cookie = f"voter_{uuid.uuid4().hex}"
    
    # 1. First vote must succeed
    res1 = client.post(
        "/api/community/vote",
        headers={"Cookie": f"dogfood_voter={test_voter_cookie}"},
        json={"project_id": "prj_01"}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # 2. Second vote by the same voter MUST be rejected with HTTP 409
    res2 = client.post(
        "/api/community/vote",
        headers={"Cookie": f"dogfood_voter={test_voter_cookie}"},
        json={"project_id": "prj_02"}
    )
    assert res2.status_code == 409
    assert "duplicate" in res2.json()["detail"].lower()

def test_cryptographic_audit_chain():
    # 1. HTML view loads
    res_html = client.get("/audit")
    assert res_html.status_code == 200
    assert "Cryptographic" in res_html.text

    # 2. JSON verification endpoint computes valid SHA-256 chain
    res_api = client.get("/api/audit/verify")
    assert res_api.status_code == 200
    data = res_api.json()
    assert data["status"] == "VALIDATED_TAMPER_FREE"
    assert len(data["chain_head"]) == 64  # Valid SHA-256 hex string
    assert data["total_blocks"] >= 100

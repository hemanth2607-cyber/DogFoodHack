import json
import os
import sys
from src.db import init_db, get_db

def seed_database(fixture_path="fixtures.json"):
    init_db()
    
    if not os.path.exists(fixture_path):
        print(f"Error: {fixture_path} not found.")
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with get_db() as conn:
        # 1. Event (CRITICAL: preserves submissions_close from fixture in the past)
        evt = data.get("event", {})
        conn.execute("""
            INSERT OR REPLACE INTO events (id, name, submissions_close)
            VALUES (?, ?, ?)
        """, (evt.get("id", "evt_01"), evt.get("name", "Sample Hack 2026"), evt.get("submissions_close", "2026-03-01T18:00:00Z")))

        # 2. Tracks
        for trk in data.get("tracks", []):
            conn.execute("INSERT OR REPLACE INTO tracks (id, name) VALUES (?, ?)", (trk["id"], trk["name"]))

        # 3. Dedicated Test Accounts
        # Organizer
        conn.execute("""
            INSERT OR REPLACE INTO users (id, name, email, role, session_token)
            VALUES (?, ?, ?, ?, ?)
        """, ("user_org", "Organizer Admin", "organizer@dogfood.local", "organizer", "org_7f2a"))

        # Participant
        conn.execute("""
            INSERT OR REPLACE INTO users (id, name, email, role, session_token)
            VALUES (?, ?, ?, ?, ?)
        """, ("user_part", "Participant Hacker", "participant@dogfood.local", "participant", "prt_2e88"))

        # 4. Judges
        judges = data.get("judges", [])
        for idx, jdg in enumerate(judges):
            j_id = jdg["id"]
            if idx == 0:
                token = "jdg_a_91bc" # judge_a
            elif idx == 1:
                token = "jdg_b_44de" # judge_b
            else:
                token = f"jdg_sess_{j_id}"

            conn.execute("""
                INSERT OR REPLACE INTO users (id, name, email, role, session_token)
                VALUES (?, ?, ?, ?, ?)
            """, (j_id, jdg.get("name", f"Judge {j_id}"), jdg.get("email"), "judge", token))

            for trk_id in jdg.get("tracks", []):
                conn.execute("INSERT OR IGNORE INTO judge_tracks (judge_id, track_id) VALUES (?, ?)", (j_id, trk_id))

        # 5. Teams & Members
        for tm in data.get("teams", []):
            conn.execute("INSERT OR REPLACE INTO teams (id, name) VALUES (?, ?)", (tm["id"], tm["name"]))
            for member_email in tm.get("members", []):
                conn.execute("INSERT OR IGNORE INTO team_members (team_id, email) VALUES (?, ?)", (tm["id"], member_email))

        # 6. Projects
        for prj in data.get("projects", []):
            conn.execute("""
                INSERT OR REPLACE INTO projects (id, team_id, track_id, title, summary, repo_url, submitted_at, is_draft)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                prj["id"],
                prj.get("team"),
                prj.get("track"),
                prj.get("title"),
                prj.get("summary"),
                prj.get("repo_url"),
                prj.get("submitted_at")
            ))

        # 7. Scores
        for sc in data.get("scores", []):
            conn.execute("""
                INSERT OR REPLACE INTO scores (judge_id, project_id, criteria_json, comment)
                VALUES (?, ?, ?, ?)
            """, (
                sc["judge"],
                sc["project"],
                json.dumps(sc.get("criteria", {})),
                sc.get("comment", "")
            ))

    print("\nseeded. test logins:")
    print("  organizer    Cookie: session=org_7f2a")
    print("  judge_a      Cookie: session=jdg_a_91bc")
    print("  judge_b      Cookie: session=jdg_b_44de")
    print("  participant  Cookie: session=prt_2e88\n")

if __name__ == "__main__":
    seed_database()

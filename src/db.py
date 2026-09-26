import sqlite3
import os
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DOGFOOD_DB_PATH", os.path.join(BASE_DIR, "dogfood.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            submissions_close TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'utc'))
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            event_id TEXT DEFAULT 'evt_01'
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            role TEXT NOT NULL, -- 'organizer', 'judge', 'participant', 'admin'
            session_token TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS judge_tracks (
            judge_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            PRIMARY KEY (judge_id, track_id),
            FOREIGN KEY (judge_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_members (
            team_id TEXT NOT NULL,
            email TEXT NOT NULL,
            user_id TEXT,
            PRIMARY KEY (team_id, email),
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            repo_url TEXT,
            submitted_at TEXT NOT NULL,
            is_draft INTEGER DEFAULT 0,
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            criteria_json TEXT NOT NULL,
            comment TEXT,
            updated_at TEXT DEFAULT (datetime('now', 'utc')),
            UNIQUE(judge_id, project_id),
            FOREIGN KEY (judge_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rubric_weights (
            criterion TEXT PRIMARY KEY,
            weight REAL NOT NULL DEFAULT 1.0
        );

        INSERT OR IGNORE INTO rubric_weights (criterion, weight) VALUES
            ('functionality', 0.40),
            ('quality', 0.35),
            ('innovation', 0.25);
        """)

if __name__ == "__main__":
    init_db()
    print("Database schema initialized at:", DB_PATH)

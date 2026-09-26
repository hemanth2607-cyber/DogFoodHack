import math
import json
from typing import Dict, List, Tuple, Any
from src.db import get_db

def compute_raw_score(criteria_dict: Dict[str, float], weights: Dict[str, float]) -> float:
    if not criteria_dict:
        return 0.0
    total_weight = 0.0
    weighted_sum = 0.0
    for crit, val in criteria_dict.items():
        w = weights.get(crit, 1.0)
        weighted_sum += float(val) * w
        total_weight += w
    return (weighted_sum / total_weight) if total_weight > 0 else (sum(criteria_dict.values()) / len(criteria_dict))

def get_normalized_scores() -> List[Dict[str, Any]]:
    with get_db() as conn:
        weights = {row["criterion"]: float(row["weight"]) for row in conn.execute("SELECT criterion, weight FROM rubric_weights")}
        
        scores_cursor = conn.execute("""
            SELECT s.judge_id, s.project_id, s.criteria_json, p.title, p.track_id, t.name as track_name
            FROM scores s
            JOIN projects p ON s.project_id = p.id
            JOIN tracks t ON p.track_id = t.id
        """)
        all_scores = scores_cursor.fetchall()

        projects_cursor = conn.execute("""
            SELECT p.id, p.title, p.track_id, t.name as track_name, p.team_id, p.repo_url, p.submitted_at
            FROM projects p
            JOIN tracks t ON p.track_id = t.id
        """)
        projects = {row["id"]: dict(row) for row in projects_cursor.fetchall()}

    if not all_scores:
        return []

    judge_ratings: Dict[str, List[float]] = {}
    record_list = []
    global_scores = []

    for row in all_scores:
        try:
            crit = json.loads(row["criteria_json"])
        except Exception:
            crit = {}
        raw = compute_raw_score(crit, weights)
        judge_id = row["judge_id"]
        proj_id = row["project_id"]
        
        judge_ratings.setdefault(judge_id, []).append(raw)
        global_scores.append(raw)
        record_list.append({
            "judge_id": judge_id,
            "project_id": proj_id,
            "raw_score": raw,
            "title": row["title"],
            "track_name": row["track_name"]
        })

    global_mean = sum(global_scores) / len(global_scores) if global_scores else 3.0
    global_var = sum((x - global_mean) ** 2 for x in global_scores) / max(len(global_scores) - 1, 1)
    global_std = math.sqrt(global_var) if global_var > 0 else 1.0

    judge_stats: Dict[str, Tuple[float, float]] = {}
    for j_id, vals in judge_ratings.items():
        m = sum(vals) / len(vals)
        var = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
        std = math.sqrt(var)
        judge_stats[j_id] = (m, std)

    project_normalized_map: Dict[str, List[float]] = {}
    project_raw_map: Dict[str, List[float]] = {}

    for rec in record_list:
        j_id = rec["judge_id"]
        p_id = rec["project_id"]
        raw = rec["raw_score"]
        m, s = judge_stats[j_id]

        if s < 1e-5:
            z = 0.0
        else:
            z = (raw - m) / s

        norm_score = max(1.0, min(5.0, global_mean + z * global_std))
        project_normalized_map.setdefault(p_id, []).append(norm_score)
        project_raw_map.setdefault(p_id, []).append(raw)

    results = []
    PRIOR_K = 1.0

    for p_id, p_info in projects.items():
        norm_list = project_normalized_map.get(p_id, [])
        raw_list = project_raw_map.get(p_id, [])
        review_count = len(norm_list)

        if review_count > 0:
            raw_avg = sum(raw_list) / review_count
            final_norm_score = (PRIOR_K * global_mean + sum(norm_list)) / (PRIOR_K + review_count)
        else:
            raw_avg = 0.0
            final_norm_score = global_mean

        results.append({
            "project_id": p_id,
            "title": p_info["title"],
            "track_id": p_info["track_id"],
            "track_name": p_info["track_name"],
            "team_id": p_info["team_id"],
            "review_count": review_count,
            "raw_score_avg": round(raw_avg, 3),
            "normalized_score": round(final_norm_score, 3)
        })

    results.sort(key=lambda x: x["normalized_score"], reverse=True)

    track_counts: Dict[str, int] = {}
    for idx, item in enumerate(results, start=1):
        item["rank"] = idx
        t_id = item["track_id"]
        track_counts[t_id] = track_counts.get(t_id, 0) + 1
        item["track_rank"] = track_counts[t_id]

    return results

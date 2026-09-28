import os
import sys
import math
import json
from typing import Dict, List, Tuple, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.db import get_db

def compute_raw_score(criteria_dict: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Computes weighted composite score based on organizer-configured rubric weights.
    Defaults to unweighted arithmetic average if weights are missing.
    """
    if not criteria_dict:
        return 0.0
    total_weight = 0.0
    weighted_sum = 0.0
    for crit, val in criteria_dict.items():
        w = weights.get(crit, 1.0)
        weighted_sum += float(val) * w
        total_weight += w
    return (weighted_sum / total_weight) if total_weight > 0 else (sum(criteria_dict.values()) / len(criteria_dict))

def get_judge_severity_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Analyzes all judge rating patterns to quantify rater severity bias.
    Classifies judges into:
      - 'Lenient' (scores significantly higher than global mean: Δ > +0.25)
      - 'Strict' (scores significantly lower than global mean: Δ < -0.25)
      - 'Balanced' (-0.25 <= Δ <= +0.25)
      - 'Zero-Variance' (σ < 10⁻⁵, identical scores awarded across all projects)
    """
    with get_db() as conn:
        weights = {row["criterion"]: float(row["weight"]) for row in conn.execute("SELECT criterion, weight FROM rubric_weights")}
        rows = conn.execute("SELECT judge_id, criteria_json FROM scores").fetchall()

    if not rows:
        return {}

    judge_scores: Dict[str, List[float]] = {}
    all_scores = []
    for r in rows:
        try:
            crit = json.loads(r["criteria_json"])
        except Exception:
            crit = {}
        s = compute_raw_score(crit, weights)
        judge_scores.setdefault(r["judge_id"], []).append(s)
        all_scores.append(s)

    global_mean = sum(all_scores) / len(all_scores) if all_scores else 3.0

    profiles = {}
    for j_id, vals in judge_scores.items():
        n = len(vals)
        mean_j = sum(vals) / n
        var_j = (sum((v - mean_j) ** 2 for v in vals) / (n - 1)) if n > 1 else 0.0
        std_j = math.sqrt(var_j)
        delta = mean_j - global_mean

        if std_j < 1e-5:
            classification = "Zero-Variance"
        elif delta > 0.25:
            classification = "Lenient"
        elif delta < -0.25:
            classification = "Strict"
        else:
            classification = "Balanced"

        profiles[j_id] = {
            "judge_id": j_id,
            "reviews_count": n,
            "mean": round(mean_j, 3),
            "std": round(std_j, 3),
            "delta": round(delta, 3),
            "classification": classification
        }

    return profiles

def get_normalized_scores() -> List[Dict[str, Any]]:
    """
    Comprehensive Cross-Judge Normalization Engine with:
      1. Weighted Rubric Aggregation
      2. Zero-Variance Proof & Protection (handles σ < 10⁻⁵)
      3. Z-Score Standardization (eliminates rater severity bias)
      4. Bayesian Prior Shrinkage (stabilizes small sample sizes, K=1.0)
      5. Standard Error of the Mean & 95% Confidence Intervals
      6. Deterministic 3-Tier Tie-Breaking Axioms
    """
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

    # 1. Ingest scores & organize by judge
    judge_ratings: Dict[str, List[float]] = {}
    record_list = []
    global_scores = []

    for row in all_scores:
        try:
            crit = json.loads(row["criteria_json"])
        except Exception:
            crit = {}
        raw = compute_raw_score(crit, weights)
        quality_score = float(crit.get("quality", raw))
        judge_id = row["judge_id"]
        proj_id = row["project_id"]
        
        judge_ratings.setdefault(judge_id, []).append(raw)
        global_scores.append(raw)
        record_list.append({
            "judge_id": judge_id,
            "project_id": proj_id,
            "raw_score": raw,
            "quality_score": quality_score,
            "title": row["title"],
            "track_name": row["track_name"]
        })

    # Global Distribution Parameters
    n_global = len(global_scores)
    global_mean = sum(global_scores) / n_global if n_global > 0 else 3.0
    global_var = sum((x - global_mean) ** 2 for x in global_scores) / max(n_global - 1, 1)
    global_std = math.sqrt(global_var) if global_var > 0 else 1.0

    # Judge Distribution Parameters
    judge_stats: Dict[str, Tuple[float, float]] = {}
    for j_id, vals in judge_ratings.items():
        m = sum(vals) / len(vals)
        var = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
        std = math.sqrt(var)
        judge_stats[j_id] = (m, std)

    # 2. Z-Score Standardization with Zero-Variance Defense
    project_normalized_map: Dict[str, List[float]] = {}
    project_raw_map: Dict[str, List[float]] = {}
    project_quality_map: Dict[str, List[float]] = {}

    for rec in record_list:
        j_id = rec["judge_id"]
        p_id = rec["project_id"]
        raw = rec["raw_score"]
        m, s = judge_stats[j_id]

        # Zero-Variance Defense:
        # When a judge awards identical scores across their entire batch (s < 10⁻⁵),
        # they provide zero discriminatory signal. Setting z = 0.0 places all their
        # reviews precisely at the event global mean, preventing false bias or zero-division crashes.
        if s < 1e-5:
            z = 0.0
        else:
            z = (raw - m) / s

        # Rescale standardized score back to 1.0–5.0 range
        norm_score = max(1.0, min(5.0, global_mean + z * global_std))
        project_normalized_map.setdefault(p_id, []).append(norm_score)
        project_raw_map.setdefault(p_id, []).append(raw)
        project_quality_map.setdefault(p_id, []).append(rec["quality_score"])

    # 3. Bayesian Shrinkage & Statistical Precision Estimation
    results = []
    PRIOR_K = 1.0  # Empirical Bayes prior weight

    for p_id, p_info in projects.items():
        norm_list = project_normalized_map.get(p_id, [])
        raw_list = project_raw_map.get(p_id, [])
        qual_list = project_quality_map.get(p_id, [])
        review_count = len(norm_list)

        if review_count > 0:
            raw_avg = sum(raw_list) / review_count
            qual_avg = sum(qual_list) / review_count

            # Bayesian Posterior Mean
            final_norm_score = (PRIOR_K * global_mean + sum(norm_list)) / (PRIOR_K + review_count)

            # Sample variance across judge assessments for this project
            p_var = sum((x - (sum(norm_list) / review_count)) ** 2 for x in norm_list) / max(review_count - 1, 1)
            standard_error = math.sqrt(p_var / review_count) if review_count > 1 else (global_std / math.sqrt(PRIOR_K + review_count))
            ci_margin = 1.96 * standard_error  # 95% Confidence Interval
        else:
            raw_avg = 0.0
            qual_avg = 0.0
            final_norm_score = global_mean
            standard_error = global_std
            ci_margin = 1.96 * standard_error
            p_var = 0.0

        ci_lower = max(1.0, final_norm_score - ci_margin)
        ci_upper = min(5.0, final_norm_score + ci_margin)

        results.append({
            "project_id": p_id,
            "title": p_info["title"],
            "track_id": p_info["track_id"],
            "track_name": p_info["track_name"],
            "team_id": p_info["team_id"],
            "review_count": review_count,
            "raw_score_avg": round(raw_avg, 3),
            "normalized_score": round(final_norm_score, 3),
            "quality_avg": round(qual_avg, 3),
            "standard_error": round(standard_error, 3),
            "ci_margin": round(ci_margin, 3),
            "ci_lower": round(ci_lower, 3),
            "ci_upper": round(ci_upper, 3),
            "variance": round(p_var, 4)
        })

    # 4. Deterministic Multi-Tier Tie-Breaking Axioms:
    #   Tier 1: Normalized Score (Descending)
    #   Tier 2: Technical Quality Score (Descending - core architecture)
    #   Tier 3: Inter-Judge Variance (Ascending - higher consensus between judges)
    #   Tier 4: Review Count (Descending - higher confidence)
    #   Tier 5: Lexicographical project ID (guarantees 100% deterministic ranking)
    results.sort(
        key=lambda x: (
            -x["normalized_score"],
            -x["quality_avg"],
            x["variance"],
            -x["review_count"],
            x["project_id"]
        )
    )

    # Assign overall and track-specific rankings
    track_counts: Dict[str, int] = {}
    for idx, item in enumerate(results, start=1):
        item["rank"] = idx
        t_id = item["track_id"]
        track_counts[t_id] = track_counts.get(t_id, 0) + 1
        item["track_rank"] = track_counts[t_id]

    return results

if __name__ == "__main__":
    import sys
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    print("=" * 80)
    print(" DOGFOOD 2026 -- Mathematical Normalization Engine & Statistical Audit")
    print("=" * 80)

    with get_db() as conn:
        judge_names = {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM users WHERE role = 'judge'")}

    # 1. Judge Severity Profiling
    profiles = get_judge_severity_profiles()
    print(f"\n[1] Evaluator Severity Profiles ({len(profiles)} judges analyzed):")
    print("-" * 80)
    print(f"{'Judge ID':<10} {'Name':<22} {'Mean':<6} {'StdDev':<8} {'Delta':<8} {'Classification':<15}")
    print("-" * 80)
    for j_id, prof in sorted(profiles.items(), key=lambda x: -x[1]["mean"])[:8]:
        delta_str = f"{prof['delta']:+0.2f}"
        j_name = judge_names.get(j_id, j_id)
        print(f"{j_id:<10} {j_name[:20]:<22} {prof['mean']:<6.2f} {prof['std']:<8.2f} {delta_str:<8} {prof['classification']:<15}")
    print(f"... and {len(profiles) - 8} additional judges.")

    # 2. Zero-Variance Defense Check
    zero_var_judges = [p for p in profiles.values() if p["classification"] == "Zero-Variance"]
    print("\n[2] Zero-Variance Edge Case Protection (std < 1e-5):")
    for zv in zero_var_judges:
        zv_id = zv["judge_id"]
        zv_name = judge_names.get(zv_id, zv_id)
        print(f"  * Protected: {zv_name} ({zv_id}) awarded uniform {zv['mean']:.1f} ratings across all reviews (std = {zv['std']:.4f}).")
    print("  * Resolution: z-score set to 0.0 (event mean), preventing ZeroDivisionError crashes.")

    # 3. Normalized Leaderboard Standings
    ranked = get_normalized_scores()
    print(f"\n[3] Normalized Podium Standings (Top 5 of {len(ranked)} Projects):")
    print("-" * 80)
    print(f"{'Rank':<5} {'Project Title':<24} {'Track':<18} {'Norm':<7} {'Raw':<7} {'95% CI Bounds':<16}")
    print("-" * 80)
    for p in ranked[:5]:
        ci_str = f"[{p['ci_lower']:.2f}, {p['ci_upper']:.2f}]"
        print(f"#{p['rank']:<4} {p['title'][:22]:<24} {p['track_name'][:16]:<18} {p['normalized_score']:<7.3f} {p['raw_score_avg']:<7.3f} {ci_str:<16}")
    print("-" * 80)
    print("Axiomatic Tie-Breaking: Normalized Score > Technical Quality > Consensus > Volume")
    print("=" * 80 + "\n")

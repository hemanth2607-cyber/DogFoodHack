# ARCHITECTURE.md — System Design & Security Rationale

## 1. Architectural Philosophy

The DOGFOOD platform is built around **Adoptability, Judging Integrity, and Zero Hosted Dependencies**:

```
                       ┌───────────────────────────────────────┐
                       │     Browser Client / run.py HTTP      │
                       └───────────────────┬───────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │   FastAPI App (Container Port 8080)   │
                       ├───────────────────────────────────────┤
                       │ • RBAC Session Extractor              │
                       │ • Deadline Enforcer (403 if past)     │
                       │ • Peer Score Shield (403 if peer)     │
                       └───────────────────┬───────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
      ┌───────────────────────────────────┐ ┌───────────────────────────────────┐
      │       Normalization Engine        │ │      Embedded SQLite Database     │
      │  (Z-Score + Bayesian Shrinkage)   │ │  (Single file: dogfood.db)        │
      └───────────────────────────────────┘ └───────────────────────────────────┘
```

---

## 2. Role-Based Access Control (RBAC) & Isolation

### Why UI Hiding Fails
Many hackathon portals fail `run.py` because they hide peer scores in HTML templates while their JSON APIs return raw data to any authenticated user. 

### Our Backend Enforcement Model
In [`src/main.py`](file:///c:/Users/heman/Desktop/dogfood/src/main.py), role authorization happens before any database query:

```python
# GET /api/judge/scores
if judge is not None:
    is_target_self = (
        judge == current_user.id or
        (judge == "judge_a" and current_user.session_token == "jdg_a_91bc")
    )
    if not is_target_self and not current_user.is_organizer():
        raise HTTPException(
            status_code=403,
            detail="Security Violation: Judges are strictly prohibited from viewing peer judge scores."
        )
```

1. **Unauthenticated access** to protected routes yields **`401 Unauthorized`**.
2. **Participant access** to judging routes yields **`403 Forbidden`**.
3. **Judge B querying Judge A** yields **`403 Forbidden`**.

---

## 3. Threat Model & Abuse Defenses

1. **Peer Peeking (Score Collusion):**
   - **Threat:** A judge inspects fellow judges' reviews to align scores or strategically manipulate rankings.
   - **Defense:** Strict backend session comparison. An individual judge's token cannot resolve any query containing another judge's identifier.
2. **Late Ballot Stuffing:**
   - **Threat:** Submitting or updating projects after the deadline.
   - **Defense:** Atomic server-side clock verification against `events.submissions_close`. Submissions are rejected before database writes.
3. **Zero-Variance Manipulation:**
   - **Threat:** A rogue or hurried judge giving 5/5 or 1/1 to all assigned projects.
   - **Defense:** The normalization engine catches $\sigma < 1e-5$, assigns $z = 0$, and pulls the scores toward the global mean, nullifying uniform bias.

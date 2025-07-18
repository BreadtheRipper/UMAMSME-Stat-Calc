from .settings import STATS, FEEDBACK_WEIGHT, PRIORITY_WEIGHTS, PRIORITY_WEIGHT_SCALE
import math
from .settings import STATS, FEEDBACK_WEIGHT
from .profiles import load_profiles

def suggest_training(current, ideal, turns, feedback=None, profile_index=None, priorities=None):
    # Build per‐action average gain vectors
    avg_gains = {}
    if profile_index is not None:
        analytics = load_profiles()[profile_index].get("analytics", {})
        astats = analytics.get("action_stats", {})
        for action, data in astats.items():
            cnt = data.get("count", 0) or 1
            avg_gains[action] = {s: data["gains"].get(s, 0) / cnt for s in STATS}
    # Fallback to 1‑point primary gain
    for a in STATS:
        avg_gains.setdefault(a, {s: (1 if s == a else 0) for s in STATS})

    # Use PRIORITY_WEIGHTS and PRIORITY_WEIGHT_SCALE from settings
    best, best_score = None, float("inf")
    for action, gains in avg_gains.items():
        total = 0.0
        for s in STATS:
            new_val = current[s] + gains[s]
            gap = new_val / ideal[s] - 1.0
            # weight feedback stat and user priority
            user_weight = 1.0
            if priorities and s in priorities:
                user_weight = PRIORITY_WEIGHTS.get(priorities[s], 1.0) * PRIORITY_WEIGHT_SCALE
            w = user_weight + (FEEDBACK_WEIGHT if feedback == s else 0.0)
            total += w * (gap * gap)
        score = math.sqrt(total)
        if score < best_score:
            best_score, best = score, action

    reason = f"Minimizes overall deviation (priorities considered, {best_score:.2f})"
    return best, reason

def race_stage(rounds_done, total_rounds):
    if rounds_done < total_rounds:
        return f"Round {rounds_done+1}"
    stages = ["Quarter-Final", "Semi-Final", "Final"]
    idx = rounds_done - total_rounds
    return stages[idx] if idx < len(stages) else "End"

from .settings import (
    STATS, FEEDBACK_WEIGHT, PRIORITY_WEIGHTS,
    PRIORITY_WEIGHT_SCALE, LOSS_REASON_WEIGHT,
    CATCHUP_THRESHOLD, CATCHUP_BOOST,
    OVERSHOOT_THRESHOLD, OVERSHOOT_PENALTY_SCALE
)
import math
from .profiles import load_profiles

def suggest_training(current, ideal, turns, feedback=None, profile_index=None, priorities=None, loss_reason_weight=None):
    """
    Suggests which stat to train next based on gap-to-ideal and weighting factors.

    Parameters:
        current (dict): Current stats {stat_name: value}.
        ideal (dict): Ideal target stats {stat_name: value}.
        turns (int): Remaining turns (not directly used here).
        feedback (str): Last feedback stat (optional).
        profile_index (int): Index of profile to load loss reasons from (optional).
        priorities (dict): User-defined priorities for each stat.
        loss_reason_weight (float): Multiplier for loss reason boost.

    Returns:
        tuple: (best_stat, reason_string, debug_weights)
    """
    loss_reasons = None

    # Load profile analytics if available
    if profile_index is not None:
        analytics = load_profiles()[profile_index].get("analytics", {})
        loss_reasons = analytics.get("loss_reasons", {})

    best_stat, best_score = None, float("-inf")
    debug_weights = {}

    print("[DEBUG] Suggestion calculations:")
    for stat in STATS:
        progress = current[stat] / ideal[stat]
        gap = 1.0 - progress  # Larger gap = further behind
        user_weight = 1.0
        note_parts = []

        # Priority weight
        priority = priorities.get(stat, "Normal") if priorities else "Normal"
        priority_weight = PRIORITY_WEIGHTS.get(priority, 1.0) * PRIORITY_WEIGHT_SCALE
        user_weight *= priority_weight
        note_parts.append(f"Priority: {priority}")

        # Catch-up boost
        if progress < CATCHUP_THRESHOLD:
            user_weight *= CATCHUP_BOOST
            note_parts.append("Catch-up boost")

        # Overshoot penalty
        if progress > OVERSHOOT_THRESHOLD:
            overshoot_ratio = progress / OVERSHOOT_THRESHOLD
            penalty = 1.0 + OVERSHOOT_PENALTY_SCALE * (overshoot_ratio - 1.0)
            user_weight /= penalty
            note_parts.append(f"Overshoot {penalty:.2f}x")

        # Feedback weight
        if feedback == stat:
            user_weight += FEEDBACK_WEIGHT
            note_parts.append("Feedback boost")

        # Loss reason weight
        if loss_reasons and stat in loss_reasons:
            lw = loss_reason_weight if loss_reason_weight is not None else LOSS_REASON_WEIGHT
            boost = lw * loss_reasons[stat]
            user_weight += boost
            note_parts.append("Loss reason boost")

        # Final score for this stat
        weighted_gap = gap * user_weight
        debug_weights[stat] = (user_weight, weighted_gap, "; ".join(note_parts))

        print(f"  {stat.capitalize():8}: Gap Δ {weighted_gap:.3f} (Weight: {user_weight:.2f}, {', '.join(note_parts)})")

        # Select if best
        if weighted_gap > best_score:
            best_score = weighted_gap
            best_stat = stat

    print(f"Selected: {best_stat.capitalize()} with total score {best_score:.3f}\n")

    reason = (
        f"Maximizes reduction of weighted stat gaps (priorities, feedback, "
        f"loss history, catch-up, overshoot considered, {best_score:.2f})"
    )
    return best_stat, reason, debug_weights



def race_stage(rounds_done, total_rounds):
    if rounds_done < total_rounds:
        return f"Round {rounds_done + 1}"
    stages = ["Quarter-Final", "Semi-Final", "Final"]
    idx = rounds_done - total_rounds
    return stages[idx] if idx < len(stages) else "End"

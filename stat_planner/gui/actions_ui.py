from PyQt6.QtWidgets import QMessageBox, QInputDialog
from pathlib import Path
from stat_planner.planner import suggest_training, race_stage
from stat_planner.settings import STATS, PHOTOS_DIR
from stat_planner.state import STATE_FILE
from stat_planner.exporter import export_run_summary

def train_action(gui):
    choice, reason, debug_weights = suggest_training(gui.current_stats, gui.ideal_stats, gui.turns_left, gui.feedback_stat)
    gui.last_action = choice
    gui.log(f"📌 Train {choice.capitalize()} — {reason}")
    # Show calculation breakdown for user clarity
    lines = ["Calculation details:"]
    lines.append("Gaps (current / ideal - 1.0):")
    for s in gui.current_stats:
        gap = gui.current_stats[s] / gui.ideal_stats[s] - 1.0 if gui.ideal_stats[s] else 0.0
        lines.append(f"  {s.capitalize()}: {gap:+.3f}")
    if debug_weights:
        lines.append("Weights used:")
        for s, w in debug_weights.items():
            lines.append(f"  {s.capitalize()}: {w:.2f}")
    lines.append("")
    lines.append("Each stat's score = weight × (gap²). The stat with the lowest total score is suggested.")
    gui.log("\n".join(lines))
    advance_turn(gui)

def recover_action(gui):
    gui.log("💤 Recovery turn")
    advance_turn(gui)

def race_action(gui):
    stage = race_stage(gui.rounds_done, gui.total_rounds)
    optional = (stage.startswith("Round") and gui.turns_left > 0)
    first, ok = QInputDialog.getItem(
        gui, "Race Result",
        "Did you come first?",
        ["Yes", "No"], 0, False
    )
    if not ok:
        return
    if first == "Yes":
        gui.log("🏆 You came first—no feedback needed.")
    else:
        if optional:
            stat, ok2 = QInputDialog.getText(
                gui, "Post‐Race Feedback",
                "Game suggested focus on which stat? (leave blank):"
            )
            if ok2 and stat.lower() in STATS:
                gui.feedback_stat = stat.lower()
                gui.log(f"💡 Optional race feedback → prioritize {stat.capitalize()}")
        else:
            # Mandatory race loss: ask for stat reason and save to profile analytics
            stat, ok2 = QInputDialog.getText(
                gui, "Loss Reason",
                "Which stat caused the loss? (leave blank if none):"
            )
            if ok2 and stat.lower() in STATS:
                idx = gui.profile_select.currentIndex()-1 if gui.profile_select.currentIndex()>0 else None
                if idx is not None:
                    from stat_planner.profiles import load_profiles, save_profiles
                    profiles = load_profiles()
                    profile = profiles[idx]
                    analytics = profile.setdefault("analytics", {})
                    loss_reasons = analytics.setdefault("loss_reasons", {})
                    loss_reasons[stat.lower()] = loss_reasons.get(stat.lower(), 0) + 1
                    save_profiles(profiles)
                    gui.log(f"📈 Recorded loss reason: {stat.capitalize()} for {profile['name']}")
            gui.log("❌ Mandatory race lost—run over.")
            if STATE_FILE.exists():
                try:
                    STATE_FILE.unlink()
                    gui.load_state_btn.setEnabled(False)
                    gui.log("🗑️ Cleared saved run state.")
                except Exception as e:
                    gui.log(f"⚠️ Could not delete saved state: {e}")
            offer_post_run_save(gui)
            return
    gui.turns_left -= 1
    gui.turn += 1
    if hasattr(gui, 'update_rounds_turns_fields'):
        gui.update_rounds_turns_fields()
    prepare_next_turn(gui)

def advance_turn(gui):
    gui.turns_left -= 1
    if hasattr(gui, 'update_rounds_turns_fields'):
        gui.update_rounds_turns_fields()
    if gui.turns_left < 1:
        handle_race_stage(gui)
    else:
        gui.turn += 1
        prepare_next_turn(gui)

def handle_race_stage(gui):
    stage = race_stage(gui.rounds_done, gui.total_rounds)
    resp = QMessageBox.question(gui, "Race", f"🏁 {stage}! Passed?")
    if resp == QMessageBox.StandardButton.Yes:
        fb, ok = QInputDialog.getText(gui, "Feedback", "Focus stat (leave blank):")
        gui.feedback_stat = fb.lower() if ok and fb.lower() in STATS else None
        gui.rounds_done += 1
        # Decrement preliminary races (total_rounds) if still in prelims
        if gui.rounds_done <= gui.total_rounds:
            gui.total_rounds -= 1
            if hasattr(gui, 'update_rounds_turns_fields'):
                gui.update_rounds_turns_fields()
        next_stage = race_stage(gui.rounds_done, gui.total_rounds)
        if next_stage == "End":
            QMessageBox.information(gui, "Done", "🏆 Final complete!")
            if STATE_FILE.exists():
                try:
                    STATE_FILE.unlink()
                    gui.load_state_btn.setEnabled(False)
                    gui.log("🗑️ Cleared saved run state.")
                except Exception as e:
                    gui.log(f"⚠️ Could not delete saved state: {e}")
            offer_post_run_save(gui)
            return
        QMessageBox.information(gui, "Next", f"Next: {next_stage}")
        turns, ok = QInputDialog.getInt(gui, "Next Turns", "Turns until next race:", min=1)
        if ok:
            gui.turns_left = turns
            gui.turn = 1
            prepare_next_turn(gui)
    else:
        # Prompt for loss reason and save to analytics
        stat, ok2 = QInputDialog.getText(
            gui, "Loss Reason",
            "Which stat caused the loss? (leave blank if none):"
        )
        if ok2 and stat.lower() in STATS:
            idx = gui.profile_select.currentIndex()-1 if gui.profile_select.currentIndex()>0 else None
            if idx is not None:
                from stat_planner.profiles import load_profiles, save_profiles
                profiles = load_profiles()
                profile = profiles[idx]
                analytics = profile.setdefault("analytics", {})
                loss_reasons = analytics.setdefault("loss_reasons", {})
                loss_reasons[stat.lower()] = loss_reasons.get(stat.lower(), 0) + 1
                save_profiles(profiles)
                gui.log(f"📈 Recorded loss reason: {stat.capitalize()} for {profile['name']}")
        QMessageBox.information(gui, "Run Over", "❌ Run ended.")
        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
                gui.load_state_btn.setEnabled(False)
                gui.log("🗑️ Cleared saved run state.")
            except Exception as e:
                gui.log(f"⚠️ Could not delete saved state: {e}")
        offer_post_run_save(gui)

def prepare_next_turn(gui):
    gui.train_btn.setEnabled(False)
    gui.recover_btn.setEnabled(False)
    gui.race_btn.setEnabled(False)
    gui.confirm_btn.setEnabled(False)
    for s in STATS:
        gui.detected_inputs[s].clear()
        gui.detected_inputs[s].setEnabled(False)
    if hasattr(gui, 'update_rounds_turns_fields'):
        gui.update_rounds_turns_fields()
    gui.log(f"🔄 Ready for turn {gui.turn}  •  {gui.turns_left} turns left until next race")

def offer_post_run_save(gui):
    resp = QMessageBox.question(gui, "Save?", "Save graph & CSV?")
    if resp == QMessageBox.StandardButton.Yes:
        gui.save_graph()
        gui.save_stats_csv()
        gui.export_to_ppt()
    gui.close()

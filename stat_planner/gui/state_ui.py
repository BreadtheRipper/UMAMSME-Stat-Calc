from PyQt6.QtWidgets import QMessageBox
from stat_planner.state import save_state, load_state, STATE_FILE
from stat_planner.settings import STATS

def on_save_state(gui):
    # Always save the current dropdown values for stat priorities
    stat_priorities = {}
    if hasattr(gui, 'priority_dropdowns'):
        for s, cb in gui.priority_dropdowns.items():
            stat_priorities[s] = cb.currentText()
    else:
        stat_priorities = gui.stat_priorities.copy() if hasattr(gui, 'stat_priorities') else None

    state = {
        "profile_index": gui.profile_select.currentIndex(),
        "ideal_stats":   gui.ideal_stats,
        "current_stats": gui.current_stats,
        "history":       gui.history,
        "feedback_stat": gui.feedback_stat,
        "total_rounds":  gui.total_rounds,
        "rounds_done":   gui.rounds_done,
        "turns_left":    gui.turns_left,
        "turn":          gui.turn,
        "stat_priorities": stat_priorities
    }
    try:
        save_state(state)
        gui.log("✅ Run state saved.")
        gui.load_state_btn.setEnabled(True)
        QMessageBox.information(gui, "Saved", "Run state saved to disk.")
    except Exception as e:
        gui.log(f"❌ Save state failed: {e}")
        QMessageBox.warning(gui, "Error", f"Could not save state:\n{e}")

def on_load_state(gui):
    data = load_state()
    if not data:
        QMessageBox.information(gui, "No State", "No saved run state found.")
        return

    # Restore stat priorities if present
    stat_priorities = data.get("stat_priorities")
    if stat_priorities:
        gui.stat_priorities = stat_priorities.copy()
        # Update dropdowns to match loaded priorities
        for s, val in stat_priorities.items():
            if s in gui.priority_dropdowns:
                gui.priority_dropdowns[s].setCurrentText(val)

    # Restore profile & UI
    idx = data.get("profile_index", 0)
    gui.profile_select.setCurrentIndex(idx)

    # Restore values
    gui.ideal_stats   = data["ideal_stats"]
    for s, val in gui.ideal_stats.items():
        gui.ideal_inputs[s].setText(str(val))

    gui.current_stats = data["current_stats"]
    # You can choose to prefill detected_inputs or leave blank until next scan

    gui.history       = data["history"]
    gui.feedback_stat = data["feedback_stat"]
    gui.total_rounds  = data["total_rounds"]
    gui.rounds_done   = data["rounds_done"]
    gui.turns_left    = data["turns_left"]
    gui.turn          = data["turn"]

    # Redraw graphs to show loaded history:
    gui.update_graph()

    # Log and ready next turn
    gui.log(f"🔄 Loaded run at turn {gui.turn} ({gui.turns_left} turns left).")
    gui.prepare_next_turn()
    QMessageBox.information(gui, "Loaded", "Run state restored.")

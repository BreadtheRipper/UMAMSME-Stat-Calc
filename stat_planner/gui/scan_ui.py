from PyQt6.QtWidgets import QMessageBox
from stat_planner.ocr import auto_read_stats
from stat_planner.settings import STATS

def scan_stats(gui):
    gui.log(f"[DEBUG] scan_stats called. turn={gui.turn}")
    if gui.turn == 0 and not gui.initialize_run():
        gui.log("[DEBUG] scan_stats: initialize_run failed or cancelled.")
        return
    gui.log("📸 Scanning...")
    stats = auto_read_stats(debug=gui.debug_toggle.isChecked())
    if not stats:
        gui.log("⚠️ Scan failed. Enter manually.")
        for s in STATS:
            gui.detected_inputs[s].clear()
            gui.detected_inputs[s].setEnabled(True)
        gui.confirm_btn.setEnabled(True)
        gui.log("[DEBUG] scan_stats: scan failed, manual entry enabled.")
        return
    gui.current_stats = stats
    for s, val in stats.items():
        gui.detected_inputs[s].setText(str(val))
        gui.detected_inputs[s].setEnabled(True)
    if gui.last_action and gui.prev_stats:
        from ..profiles import record_action_gain
        idx = gui.profile_select.currentIndex() - 1
        record_action_gain(idx, gui.last_action, gui.prev_stats, stats)
        gui.log(f"💾 Learned gains for {gui.last_action}")
        gui.last_action = None
        gui.prev_stats  = None
    gui.confirm_btn.setEnabled(True)
    gui.train_btn.setEnabled(False)
    gui.recover_btn.setEnabled(False)
    gui.log("✅ Scan complete.")

def confirm_stats(gui):
    gui.log("[DEBUG] confirm_stats called.")
    try:
        gui.current_stats = {s: int(gui.detected_inputs[s].text()) for s in STATS}
    except Exception as e:
        gui.log(f"[DEBUG] confirm_stats error: {e}")
        QMessageBox.warning(gui, "Input Error", "Enter valid ints.")
        return
    gui.history.append(gui.current_stats.copy())
    gui.log(f"[DEBUG] confirm_stats: current_stats set to {gui.current_stats}")
    gui.update_graph()
    gui.log(f"✅ Stats confirmed: {gui.current_stats}")
    gui.train_btn.setEnabled(True)
    gui.recover_btn.setEnabled(True)
    gui.race_btn.setEnabled(True)
    gui.confirm_btn.setEnabled(False)
    gui.prev_stats = gui.current_stats.copy()

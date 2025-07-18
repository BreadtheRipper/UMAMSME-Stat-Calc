from PyQt6.QtWidgets import QMessageBox
from .ocr import auto_read_stats
from .settings import STATS

def scan_stats(gui):
    if gui.turn == 0 and not gui.initialize_run():
        return
    gui.log("📸 Scanning...")
    stats = auto_read_stats(debug=gui.debug_toggle.isChecked())
    if not stats:
        gui.log("⚠️ Scan failed. Enter manually.")
        for s in STATS:
            gui.detected_inputs[s].clear()
            gui.detected_inputs[s].setEnabled(True)
        gui.confirm_btn.setEnabled(True)
        return
    gui.current_stats = stats
    for s, val in stats.items():
        gui.detected_inputs[s].setText(str(val))
        gui.detected_inputs[s].setEnabled(True)
    # inside StatPlannerGUI.scan_stats(), after stats obtained:
    if gui.last_action and gui.prev_stats:
        from .profiles import record_action_gain
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
    try:
        gui.current_stats = {s: int(gui.detected_inputs[s].text()) for s in STATS}
    except:
        QMessageBox.warning(gui, "Input Error", "Enter valid ints.")
        return
    gui.history.append(gui.current_stats.copy())
    gui.update_graph()
    gui.log(f"✅ Stats confirmed: {gui.current_stats}")
    gui.train_btn.setEnabled(True)
    gui.recover_btn.setEnabled(True)
    gui.race_btn.setEnabled(True)
    gui.confirm_btn.setEnabled(False)
    gui.prev_stats = gui.current_stats.copy()

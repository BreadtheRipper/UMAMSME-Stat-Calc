import sys, csv, shutil
from pathlib import Path
import traceback
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QMessageBox, QTextEdit, QCheckBox, QInputDialog,
    QComboBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox, QSplitter
)
from PyQt6.QtGui import QPixmap, QIcon, QIntValidator
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from stat_planner.gui.graph_ui import setup_graphs, update_graph
from stat_planner.gui.state_ui import on_save_state, on_load_state
from stat_planner.gui.scan_ui import scan_stats, confirm_stats
from stat_planner.gui.actions_ui import train_action, recover_action, race_action
from stat_planner.gui.profile_ui import on_profile_selected, show_add_profile_dialog, show_edit_profile_dialog
import json
from .exporter import export_run_summary
from .state import STATE_FILE

from .settings   import STATS, ICON_PATH, PHOTOS_DIR
from .assets     import load_stat_icons
from .ocr        import auto_read_stats
from .planner    import suggest_training, race_stage
from .profiles   import load_profiles

class StatPlannerGUI(QWidget):
    def __init__(self):
        print("[DEBUG] StatPlannerGUI.__init__ start")
        super().__init__()
        # (try/except is at the end of this method)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
    def __init__(self):
        super().__init__()
        try:
            self.setWindowIcon(QIcon(str(ICON_PATH)))
            self.setWindowTitle("🎯 Stat Planner")
            self.resize(900, 800)

            # --- State ---
            self.ideal_stats = {}
            self.current_stats = {}
            self.history = []
            self.feedback_stat = None
            self.total_rounds = self.rounds_done = 0
            self.turns_left = self.turn = 0
            self.last_action = None
            self.prev_stats  = None

            self.stat_priorities = {s: 'Normal' for s in STATS}
            self.priority_dropdowns = {}
            self.stat_icons = load_stat_icons()
            self.profiles = load_profiles()

            # --- Main content layout ---
            self.main_content = QWidget()
            main_layout = QVBoxLayout(self.main_content)
            self.main_layout = main_layout

            # --- Profile selector ---
            profile_layout = QHBoxLayout()
            profile_layout.addWidget(QLabel("Trainee:"))
            self.profile_select = QComboBox()
            self.profile_select.addItem("— Select Trainee —")
            for p in self.profiles:
                self.profile_select.addItem(p["name"])
            self.profile_select.currentIndexChanged.connect(lambda idx: on_profile_selected(self, idx))
            profile_layout.addWidget(self.profile_select)
            self.photo_lbl = QLabel()
            profile_layout.addWidget(self.photo_lbl)
            self.add_profile_btn = QPushButton("Add Trainee…")
            self.add_profile_btn.clicked.connect(lambda: show_add_profile_dialog(self))
            profile_layout.addWidget(self.add_profile_btn)
            self.edit_profile_btn = QPushButton("Edit Trainee…")
            self.edit_profile_btn.clicked.connect(lambda: show_edit_profile_dialog(self))
            profile_layout.addWidget(self.edit_profile_btn)
            main_layout.addLayout(profile_layout)


            # --- Ideal Stats & Stat Priorities (aligned columns) ---
            aligned_layout = QHBoxLayout()
            aligned_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.ideal_inputs = {}
            self.priority_dropdowns = {}
            stat_columns = []
            priority_options = ["Lowest", "Low", "Normal", "High", "Highest"]
            for stat in STATS:
                col = QVBoxLayout()
                col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                # Icon + Stat name
                h = QHBoxLayout()
                h.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                icon = QLabel()
                pix = self.stat_icons[stat]
                if pix:
                    icon.setPixmap(pix.scaled(24,24,Qt.AspectRatioMode.KeepAspectRatio))
                h.addWidget(icon)
                h.addWidget(QLabel(stat.capitalize()))
                col.addLayout(h)
                # Ideal stat input
                le = QLineEdit()
                le.setFixedWidth(60)
                col.addWidget(le)
                self.ideal_inputs[stat] = le
                # Stat priority dropdown
                cb = QComboBox()
                cb.addItems(priority_options)
                cb.setCurrentText("Normal")
                cb.currentTextChanged.connect(lambda val, s=stat: self.set_stat_priority(s, val))
                col.addWidget(cb)
                self.priority_dropdowns[stat] = cb
                stat_columns.append(col)
            # Add all stat columns to the aligned layout
            for col in stat_columns:
                aligned_layout.addLayout(col)
            main_layout.addLayout(aligned_layout)

            # --- Rounds/Turns (stacked left) + Loss Reason Weight (right) ---
            from stat_planner.settings import LOSS_REASON_WEIGHT
            from PyQt6.QtGui import QDoubleValidator
            row = QHBoxLayout()
            # Left: rounds/turns stacked
            rounds_stack = QVBoxLayout()
            rounds_stack.setAlignment(Qt.AlignmentFlag.AlignLeft)
            from PyQt6.QtWidgets import QSizePolicy
            rounds_row1 = QHBoxLayout()
            rounds_row1.setSpacing(4)
            rounds_row1.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label1 = QLabel("Total Rounds (before QF):")
            label1.setMinimumWidth(0)
            label1.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            rounds_row1.addWidget(label1)
            self.total_rounds_input = QLineEdit()
            self.total_rounds_input.setFixedWidth(60)
            self.total_rounds_input.setValidator(QIntValidator(1, 99))
            rounds_row1.addWidget(self.total_rounds_input)
            rounds_row1.addStretch(1)
            rounds_stack.addLayout(rounds_row1)
            rounds_row2 = QHBoxLayout()
            rounds_row2.setSpacing(4)
            rounds_row2.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label2 = QLabel("Turns Until Next Race:")
            label2.setMinimumWidth(0)
            label2.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            rounds_row2.addWidget(label2)
            self.turns_total_input = QLineEdit()
            self.turns_total_input.setFixedWidth(60)
            self.turns_total_input.setValidator(QIntValidator(1, 99))
            rounds_row2.addWidget(self.turns_total_input)
            rounds_row2.addStretch(1)
            rounds_stack.addLayout(rounds_row2)
            row.addLayout(rounds_stack)
            # Right: loss reason weight
            loss_weight_box = QVBoxLayout()
            loss_weight_box.setAlignment(Qt.AlignmentFlag.AlignTop)
            loss_weight_box.addWidget(QLabel("Loss Reason Weight:"))
            self.loss_reason_weight_input = QLineEdit(str(LOSS_REASON_WEIGHT))
            self.loss_reason_weight_input.setFixedWidth(50)
            self.loss_reason_weight_input.setValidator(QDoubleValidator(0.0, 1000.0, 3))
            self.loss_reason_weight_input.setToolTip("Each loss increases the stat's weight by this factor (e.g. 0.2)")
            loss_weight_box.addWidget(self.loss_reason_weight_input)
            row.addLayout(loss_weight_box)
            main_layout.addLayout(row)

            # --- Detected Stats Inputs (icon next to stat name, value below) ---
            det = QHBoxLayout()
            det.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.detected_inputs = {}
            for stat in STATS:
                v = QVBoxLayout()
                v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                h = QHBoxLayout()
                h.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                icon = QLabel()
                pix = self.stat_icons[stat]
                if pix:
                    icon.setPixmap(pix.scaled(24,24,Qt.AspectRatioMode.KeepAspectRatio))
                h.addWidget(icon)
                h.addWidget(QLabel(stat.capitalize()))
                v.addLayout(h)
                le = QLineEdit()
                le.setFixedWidth(60)
                v.addWidget(le)
                det.addLayout(v)
                self.detected_inputs[stat] = le
            main_layout.addLayout(det)

            # --- Buttons: Scan & Confirm ---
            btns = QHBoxLayout()
            self.scan_btn    = QPushButton("Scan Stats")
            self.scan_btn.clicked.connect(lambda: scan_stats(self))
            self.confirm_btn = QPushButton("Confirm Stats")
            self.confirm_btn.clicked.connect(lambda: confirm_stats(self))
            self.confirm_btn.setEnabled(False)
            btns.addWidget(self.scan_btn)
            btns.addWidget(self.confirm_btn)
            main_layout.addLayout(btns)

            # --- Train/Recover ---
            ar = QHBoxLayout()
            self.train_btn   = QPushButton("Train")
            self.train_btn.clicked.connect(self.train_action)
            self.recover_btn = QPushButton("Recover")
            self.recover_btn.clicked.connect(self.recover_action)
            self.race_btn = QPushButton("Race")
            self.race_btn.clicked.connect(lambda: race_action(self))
            self.train_btn.setEnabled(False)
            self.recover_btn.setEnabled(False)
            self.race_btn.setEnabled(False)
            ar.addWidget(self.train_btn)
            ar.addWidget(self.recover_btn)
            ar.addWidget(self.race_btn)
            main_layout.addLayout(ar)

            # --- Graphs ---
            setup_graphs(self)

            # --- Save buttons ---
            sv = QHBoxLayout()
            self.save_png_btn = QPushButton("Save Graph as PNG")
            self.save_png_btn.clicked.connect(self.save_graph)
            self.save_csv_btn = QPushButton("Export Stats to CSV")
            self.save_csv_btn.clicked.connect(self.save_stats_csv)
            sv.addWidget(self.save_png_btn)
            sv.addWidget(self.save_csv_btn)
            self.export_ppt_btn = QPushButton("Export to PowerPoint")
            self.export_ppt_btn.clicked.connect(self.export_to_ppt)
            sv.addWidget(self.export_ppt_btn)
            self.save_state_btn = QPushButton("Save Run State")
            self.save_state_btn.clicked.connect(lambda: on_save_state(self))
            sv.addWidget(self.save_state_btn)
            self.load_state_btn = QPushButton("Load Run State")
            self.load_state_btn.clicked.connect(lambda: on_load_state(self))
            self.load_state_btn.setEnabled(STATE_FILE.exists())
            sv.addWidget(self.load_state_btn)
            main_layout.addLayout(sv)

            # --- Debug toggle ---
            dbg = QHBoxLayout()
            self.debug_toggle = QCheckBox("Show Debug Image After Scan")
            dbg.addWidget(self.debug_toggle)
            main_layout.addLayout(dbg)

            # --- Status log (Resizable & Pop-out) ---
            self.status_output = QTextEdit()
            self.status_output.setReadOnly(True)
            self.popout_btn = QPushButton("Pop Out Log")
            self.popout_btn.setToolTip("Open the log/output area in a separate window")
            self.popout_btn.clicked.connect(self.popout_log_window)

            self.splitter = QSplitter(Qt.Orientation.Vertical)
            self.splitter.addWidget(self.main_content)
            log_widget = QWidget()
            log_layout = QVBoxLayout(log_widget)
            log_layout.setContentsMargins(0,0,0,0)
            log_layout.addWidget(self.status_output)
            log_layout.addWidget(self.popout_btn)
            self.splitter.addWidget(log_widget)
            self.splitter.setSizes([600, 200])
            layout = QVBoxLayout(self)
            layout.addWidget(self.splitter)
            self.setLayout(layout)

        except Exception as e:
            print("[ERROR] Exception in StatPlannerGUI.__init__:")
            traceback.print_exc()
        except Exception as e:
            print("[ERROR] Exception in StatPlannerGUI.__init__:")
            traceback.print_exc()
            self.load_state_btn.clicked.connect(lambda: on_load_state(self))
            self.load_state_btn.setEnabled(STATE_FILE.exists())
            sv.addWidget(self.load_state_btn)
            main_layout.addLayout(sv)
            print("[DEBUG] Save/export buttons added")

            # --- Debug toggle ---
            dbg = QHBoxLayout()
            self.debug_toggle = QCheckBox("Show Debug Image After Scan")
            dbg.addWidget(self.debug_toggle)
            main_layout.addLayout(dbg)
            print("[DEBUG] Debug toggle added")

            # --- Status log (Resizable & Pop-out) ---
            self.status_output = QTextEdit()
            self.status_output.setReadOnly(True)
            self.popout_btn = QPushButton("Pop Out Log")
            self.popout_btn.setToolTip("Open the log/output area in a separate window")
            self.popout_btn.clicked.connect(self.popout_log_window)

            # --- Use QSplitter for resizable main content and log ---
            self.splitter = QSplitter(Qt.Orientation.Vertical)
            self.splitter.addWidget(self.main_content)
            log_widget = QWidget()
            log_layout = QVBoxLayout(log_widget)
            log_layout.setContentsMargins(0,0,0,0)
            log_layout.addWidget(self.status_output)
            log_layout.addWidget(self.popout_btn)
            self.splitter.addWidget(log_widget)
            self.splitter.setSizes([500, 150])
            # Set the main layout to just the splitter
            layout = QVBoxLayout(self)
            layout.addWidget(self.splitter)
            self.setLayout(layout)
            print("[DEBUG] Status log and pop-out added (splitter main layout)")
            print("[DEBUG] Main layout set. StatPlannerGUI.__init__ end")
        except Exception as e:
            print("[ERROR] Exception in StatPlannerGUI.__init__:")
            traceback.print_exc()


    def popout_log_window(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Log Output")
        dlg.resize(600, 400)
        layout = QVBoxLayout()
        log_copy = QTextEdit()
        log_copy.setReadOnly(True)
        log_copy.setText(self.status_output.toPlainText())
        layout.addWidget(log_copy)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.setLayout(layout)
        dlg.exec()

    def get_loss_reason_weight(self):
        try:
            val = float(self.loss_reason_weight_input.text())
            return val
        except Exception:
            return 0.2

    def set_stat_priority(self, stat, value):
        self.stat_priorities[stat] = value
        # Optionally, log or trigger UI update if needed
        self.log(f"Priority for {stat.capitalize()} set to {value}.")

    # --- Profile Handlers moved to profile_ui.py ---

    def log(self, msg): 
        self.status_output.append(msg)

    def initialize_run(self):
        try:
            self.ideal_stats = {s:int(self.ideal_inputs[s].text()) for s in STATS}
            self.total_rounds = int(self.total_rounds_input.text())
            self.turns_left  = int(self.turns_total_input.text())
            self.turn = 1; self.rounds_done = 0; self.feedback_stat = None; self.history.clear()
            # Make rounds/turns fields read-only after run starts
            self.total_rounds_input.setReadOnly(True)
            self.turns_total_input.setReadOnly(True)
            self.log("✅ Run initialized.")
            self.update_rounds_turns_fields()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Input Error", "Enter valid integers.")
            return False

    # --- Scan/Confirm Handlers moved to scan_ui.py ---

    def train_action(self):
        loss_reason_weight = self.get_loss_reason_weight() if hasattr(self, 'get_loss_reason_weight') else 0.2
        choice, reason, debug_weights = suggest_training(
            self.current_stats,
            self.ideal_stats,
            self.turns_left,
            self.feedback_stat,
            priorities=self.stat_priorities,
            profile_index=self.profile_select.currentIndex()-1 if self.profile_select.currentIndex()>0 else None,
            loss_reason_weight=loss_reason_weight
        )
        self.last_action = choice
        # Refined display: weights in a table-like format
        self.log(f"📌 Train {choice.capitalize()} — {reason}")
        lines = ["<b>Weights used:</b>", "<pre>  Stat      Weight"]
        for s, w in debug_weights.items():
            lines.append(f"  {s.capitalize():8} {w:6.2f}")
        lines.append("</pre>")
        self.log("\n".join(lines))
        self.advance_turn()

    def recover_action(self):
        self.log("💤 Recovery turn")
        self.advance_turn()

    def advance_turn(self):
        self.turns_left -= 1
        self.update_rounds_turns_fields()
        if self.turns_left < 1:
            self.handle_race_stage()
        else:
            self.turn += 1
            self.prepare_next_turn()

    def handle_race_stage(self):
        stage = race_stage(self.rounds_done, self.total_rounds)
        resp = QMessageBox.question(self, "Race", f"🏁 {stage}! Passed?")
        if resp == QMessageBox.StandardButton.Yes:
            fb, ok = QInputDialog.getText(self, "Feedback", "Focus stat (leave blank):")
            self.feedback_stat = fb.lower() if ok and fb.lower() in STATS else None
            self.rounds_done += 1
            self.update_rounds_turns_fields()
            next_stage = race_stage(self.rounds_done, self.total_rounds)
            if next_stage == "End":
                QMessageBox.information(self, "Done", "🏆 Final complete!")
                # Remove the saved state file if it exists
                if STATE_FILE.exists():
                    try:
                        STATE_FILE.unlink()
                        self.load_state_btn.setEnabled(False)
                        self.log("🗑️ Cleared saved run state.")
                    except Exception as e:
                        self.log(f"⚠️ Could not delete saved state: {e}")
                self.offer_post_run_save(); return
            QMessageBox.information(self, "Next", f"Next: {next_stage}")
            turns, ok = QInputDialog.getInt(self, "Next Turns", "Turns until next race:", min=1)
            if ok:
                self.turns_left = turns; self.turn = 1; self.update_rounds_turns_fields(); self.prepare_next_turn()
        else:
            # Prompt for loss reason and save to analytics
            stat, ok2 = QInputDialog.getText(self, "Loss Reason", "Which stat caused the loss? (leave blank if none):")
            if ok2 and stat.lower() in STATS:
                idx = self.profile_select.currentIndex()-1 if self.profile_select.currentIndex()>0 else None
                if idx is not None:
                    import json
                    from stat_planner.profiles import load_profiles, save_profiles
                    profiles = load_profiles()
                    profile = profiles[idx]
                    analytics = profile.setdefault("analytics", {})
                    loss_reasons = analytics.setdefault("loss_reasons", {})
                    loss_reasons[stat.lower()] = loss_reasons.get(stat.lower(), 0) + 1
                    save_profiles(profiles)
                    self.log(f"📈 Recorded loss reason: {stat.capitalize()} for {profile['name']}")
            QMessageBox.information(self, "Run Over", "❌ Run ended.")
            # Remove the saved state file if it exists
            if STATE_FILE.exists():
                try:
                    STATE_FILE.unlink()
                    self.load_state_btn.setEnabled(False)
                    self.log("🗑️ Cleared saved run state.")
                except Exception as e:
                    self.log(f"⚠️ Could not delete saved state: {e}")
            self.offer_post_run_save()

    def prepare_next_turn(self):
        self.train_btn.setEnabled(False); self.recover_btn.setEnabled(False); self.race_btn.setEnabled(False); self.confirm_btn.setEnabled(False)
        for s in STATS:
            self.detected_inputs[s].clear(); self.detected_inputs[s].setEnabled(False)
        self.update_rounds_turns_fields()
        # combined message:
        self.log(f"🔄 Ready for turn {self.turn}  •  {self.turns_left} turns left until next race")

    def update_rounds_turns_fields(self):
        # Always reflect the current state in the fields
        self.total_rounds_input.setText(str(self.total_rounds))
        self.turns_total_input.setText(str(self.turns_left))
        # Make them read-only after run starts
        self.total_rounds_input.setReadOnly(True)
        self.turns_total_input.setReadOnly(True)

    def reset_rounds_turns_fields(self):
        # Allow editing again (e.g. after run ends or on new run)
        self.total_rounds_input.setReadOnly(False)
        self.turns_total_input.setReadOnly(False)

    def offer_post_run_save(self):
        resp = QMessageBox.question(self, "Save?", "Save graph & CSV?")
        if resp == QMessageBox.StandardButton.Yes:
            self.save_graph(); self.save_stats_csv(); self.export_to_ppt()
        # Allow editing rounds/turns for next run
        self.reset_rounds_turns_fields()
        self.close()

    def update_graph(self):
        update_graph(self)

    def save_graph(self):
        try:
            from pyqtgraph.exporters import ImageExporter
            ie = ImageExporter(self.graph.plotItem)
            ie.export("stat_graph.png")
            self.log("✅ Graph saved.")
        except Exception as e:
            self.log(f"❌ Save graph error: {e}")

    def save_stats_csv(self):
        try:
            with open("stat_history.csv","w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["Turn"]+STATS)
                w.writeheader()
                for i,r in enumerate(self.history,1):
                    w.writerow({"Turn":i,**r})
            self.log("✅ CSV saved.")
        except Exception as e:
            self.log(f"❌ Save CSV error: {e}")
    
    def export_to_ppt(self):
        trainee = self.profile_select.currentText() or "Run"
        photo = None
        idx = self.profile_select.currentIndex()
        if idx > 0:
            photo = str(Path(PHOTOS_DIR) / self.profiles[idx-1]["photo"]) if self.profiles[idx-1].get("photo") else None
        export_run_summary(self.history, self.ideal_stats, trainee, photo)
        QMessageBox.information(self, "Export Complete", "run_summary.pptx created!")
    
    # --- State Handlers moved to state_ui.py ---

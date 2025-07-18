import sys, csv, shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QMessageBox, QTextEdit, QCheckBox, QInputDialog,
    QComboBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtGui import QPixmap, QIcon, QIntValidator
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from stat_planner.gui.graph_ui import setup_graphs, update_graph
from stat_planner.gui.state_ui import on_save_state, on_load_state
from stat_planner.gui.scan_ui import scan_stats, confirm_stats
from stat_planner.gui.actions_ui import train_action, recover_action, race_action
from stat_planner.gui.profile_ui import on_profile_selected, show_add_profile_dialog
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
        super().__init__()
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setWindowTitle("🎯 Stat Planner")
        self.resize(800,700)

        # --- State ---
        self.ideal_stats = {}
        self.current_stats = {}
        self.history = []
        self.feedback_stat = None
        self.total_rounds = self.rounds_done = 0
        self.turns_left = self.turn = 0
        self.last_action = None
        self.prev_stats  = None

        # --- Stat priorities ---
        self.stat_priorities = {s: 'Normal' for s in STATS}
        self.priority_dropdowns = {}

        # --- Load assets & profiles ---
        self.stat_icons = load_stat_icons()
        self.profiles = load_profiles()

        # --- Build UI ---
        self.main_layout = QVBoxLayout()

        # --- Profile selector + Add button ---
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
        self.main_layout.addLayout(profile_layout)

        # --- Ideal stat inputs ---
        ideal_layout = QHBoxLayout()
        self.ideal_inputs = {}
        for stat in STATS:
            v = QVBoxLayout()
            icon = QLabel()
            pix = self.stat_icons[stat]
            if pix:
                icon.setPixmap(pix.scaled(24,24,Qt.AspectRatioMode.KeepAspectRatio))
            v.addWidget(icon)
            v.addWidget(QLabel(f"Ideal {stat.capitalize()}:"))
            le = QLineEdit()
            le.setFixedWidth(60)
            le.setValidator(QIntValidator(0, 9999))
            v.addWidget(le)
            ideal_layout.addLayout(v)
            self.ideal_inputs[stat] = le
        self.main_layout.addLayout(ideal_layout)

        # --- Stat Priority Controls ---
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Stat Priorities:"))
        priority_options = ["Lowest", "Low", "Normal", "High", "Highest"]
        for stat in STATS:
            v = QVBoxLayout()
            v.addWidget(QLabel(stat.capitalize()))
            cb = QComboBox()
            cb.addItems(priority_options)
            cb.setCurrentText("Normal")
            cb.currentTextChanged.connect(lambda val, s=stat: self.set_stat_priority(s, val))
            v.addWidget(cb)
            priority_layout.addLayout(v)
            self.priority_dropdowns[stat] = cb
        self.main_layout.addLayout(priority_layout)

        # --- Rounds & turns ---
        rr = QHBoxLayout()
        rr.addWidget(QLabel("Preliminary Races (before Quarter-Finals):"))
        self.total_rounds_input = QLineEdit()
        self.total_rounds_input.setFixedWidth(60)
        self.total_rounds_input.setValidator(QIntValidator(1, 99))
        rr.addWidget(self.total_rounds_input)
        self.main_layout.addLayout(rr)

        tr = QHBoxLayout()
        tr.addWidget(QLabel("Turns until next race:"))
        self.turns_total_input = QLineEdit()
        self.turns_total_input.setFixedWidth(60)
        self.turns_total_input.setValidator(QIntValidator(1, 99))
        tr.addWidget(self.turns_total_input)
        self.main_layout.addLayout(tr)

        # --- Detected stats ---
        self.main_layout.addWidget(QLabel("Detected Stats (edit if needed):"))
        det = QHBoxLayout()
        self.detected_inputs = {}
        for stat in STATS:
            v = QVBoxLayout()
            icon = QLabel()
            pix = self.stat_icons[stat]
            if pix:
                icon.setPixmap(pix.scaled(24,24,Qt.AspectRatioMode.KeepAspectRatio))
            v.addWidget(icon)
            le = QLineEdit()
            le.setFixedWidth(60)
            v.addWidget(le)
            det.addLayout(v)
            self.detected_inputs[stat] = le
        self.main_layout.addLayout(det)

        # --- Buttons: Scan & Confirm ---
        btns = QHBoxLayout()
        self.scan_btn    = QPushButton("Scan Stats")
        self.scan_btn.clicked.connect(lambda: scan_stats(self))
        self.confirm_btn = QPushButton("Confirm Stats")
        self.confirm_btn.clicked.connect(lambda: confirm_stats(self))
        self.confirm_btn.setEnabled(False)
        btns.addWidget(self.scan_btn)
        btns.addWidget(self.confirm_btn)
        self.main_layout.addLayout(btns)

        # --- Train/Recover ---
        ar = QHBoxLayout()
        self.train_btn   = QPushButton("Train")
        self.train_btn.clicked.connect(lambda: train_action(self))
        self.recover_btn = QPushButton("Recover")
        self.recover_btn.clicked.connect(lambda: recover_action(self))
        self.race_btn = QPushButton("Race")
        self.race_btn.clicked.connect(lambda: race_action(self))
        self.train_btn.setEnabled(False)
        self.recover_btn.setEnabled(False)
        self.race_btn.setEnabled(False)
        ar.addWidget(self.train_btn)
        ar.addWidget(self.recover_btn)
        ar.addWidget(self.race_btn)
        self.main_layout.addLayout(ar)

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
        # after your existing save_png_btn / save_csv_btn / export_ppt_btn
        self.save_state_btn = QPushButton("Save Run State")
        self.save_state_btn.clicked.connect(lambda: on_save_state(self))
        sv.addWidget(self.save_state_btn)

        self.load_state_btn = QPushButton("Load Run State")
        self.load_state_btn.clicked.connect(lambda: on_load_state(self))
        # Disable if there's no save file on disk
        self.load_state_btn.setEnabled(STATE_FILE.exists())
        sv.addWidget(self.load_state_btn)

        self.main_layout.addLayout(sv)

        # --- Debug toggle ---
        dbg = QHBoxLayout()
        self.debug_toggle = QCheckBox("Show Debug Image After Scan")
        dbg.addWidget(self.debug_toggle)
        self.main_layout.addLayout(dbg)

        # --- Status log ---
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setFixedHeight(150)
        self.main_layout.addWidget(self.status_output)

        self.setLayout(self.main_layout)

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
        choice, reason = suggest_training(
            self.current_stats,
            self.ideal_stats,
            self.turns_left,
            self.feedback_stat,
            priorities=self.stat_priorities
        )
        self.last_action = choice
        self.log(f"📌 Train {choice.capitalize()} — {reason}")
        self.advance_turn()

    def recover_action(self):
        self.log("💤 Recovery turn")
        self.advance_turn()
        
    def race_action(self):
        # Determine if this is an “optional race” vs a mandatory one:
        stage = race_stage(self.rounds_done, self.total_rounds)
        optional = (stage.startswith("Round") and self.turns_left > 0)
        
        first, ok = QInputDialog.getItem(
            self, "Race Result",
            "Did you come first?",
            ["Yes", "No"], 0, False
        )
        if not ok: return

        if first == "Yes":
            self.log("🏆 You came first—no feedback needed.")
        else:
            # Optional race feedback
            if optional:
                stat, ok2 = QInputDialog.getText(
                    self, "Post‐Race Feedback",
                    "Game suggested focus on which stat? (leave blank):"
                )
                if ok2 and stat.lower() in STATS:
                    self.feedback_stat = stat.lower()
                    self.log(f"💡 Optional race feedback → prioritize {stat.capitalize()}")
                    # here we’ll record this feedback into the profile’s history
            else:
                # Mandatory race loss ends run
                self.log("❌ Mandatory race lost—run over.")
                # Remove the saved state file if it exists
                if STATE_FILE.exists():
                    try:
                        STATE_FILE.unlink()
                        self.load_state_btn.setEnabled(False)
                        self.log("🗑️ Cleared saved run state.")
                    except Exception as e:
                        self.log(f"⚠️ Could not delete saved state: {e}")
                self.offer_post_run_save()
                return

        # after handling feedback, treat it like a turn—do NOT decrement turns_left!
        self.turn += 1
        self.prepare_next_turn()

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

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

        # --- Load assets & profiles ---
        self.stat_icons = load_stat_icons()
        self.profiles = load_profiles()

        # --- Build UI ---
        main = QVBoxLayout()
        self.main_layout = main  # For graph_ui.py to access

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
        main.addLayout(profile_layout)

        # --- Ideal stat inputs ---
        ideal_layout = QHBoxLayout()
        self.ideal_inputs = {}
        for stat in STATS:
            v = QVBoxLayout()
            icon = QLabel()
            pix = self.stat_icons[stat]

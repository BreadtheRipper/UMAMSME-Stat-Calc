from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox
from PyQt6.QtGui import QIntValidator, QPixmap
from PyQt6.QtCore import Qt
from pathlib import Path
from .settings import STATS, PHOTOS_DIR
from .profiles import add_profile


def on_profile_selected(gui, idx):
    if idx <= 0:
        return
    profile = gui.profiles[idx-1]
    # Fill ideal stats
    for stat, val in profile["ideal_stats"].items():
        gui.ideal_inputs[stat].setText(str(val))
    # Show photo if present
    if profile.get("photo"):
        photo_file = PHOTOS_DIR / profile["photo"]
        pix = QPixmap(str(photo_file))
        gui.photo_lbl.setPixmap(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
    else:
        gui.photo_lbl.clear()

def show_add_profile_dialog(gui):
    dlg = QDialog(gui)
    dlg.setWindowTitle("Add New Trainee")
    form = QFormLayout(dlg)

    name_edit = QLineEdit(); form.addRow("Name:", name_edit)
    ideals = {}
    for stat in STATS:
        le = QLineEdit()
        le.setValidator(QIntValidator(0,9999))
        form.addRow(f"Ideal {stat.capitalize()}:", le)
        ideals[stat] = le

    photo_btn = QPushButton("Choose Photo…")
    photo_path = {"val": None}
    def pick_photo():
        p, _ = QFileDialog.getOpenFileName(gui, "Select Photo", "", "Images (*.png *.jpg *.jpeg)")
        if p:
            photo_path["val"] = p
            photo_btn.setText(Path(p).name)
    photo_btn.clicked.connect(pick_photo)
    form.addRow("Photo:", photo_btn)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                               QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    form.addRow(buttons)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        name = name_edit.text().strip()
        if not name:
            QMessageBox.warning(gui, "Error", "Name cannot be blank.")
            return
        stats = {s:int(ideals[s].text() or 0) for s in STATS}
        gui.profiles = add_profile(name, stats, photo_path["val"])
        # Reload dropdown
        gui.profile_select.clear()
        gui.profile_select.addItem("— Select Trainee —")
        for p in gui.profiles:
            gui.profile_select.addItem(p["name"])
        QMessageBox.information(gui, "Success", f"Trainee '{name}' added.")


from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox
from PyQt6.QtGui import QIntValidator, QPixmap
from PyQt6.QtCore import Qt
from pathlib import Path
from stat_planner.settings import STATS, PHOTOS_DIR
from stat_planner.profiles import add_profile, load_profiles, save_profiles

def show_edit_profile_dialog(gui):
    idx = gui.profile_select.currentIndex() - 1
    if idx < 0:
        QMessageBox.information(gui, "Edit Profile", "Select a trainee to edit.")
        return
    profiles = load_profiles()
    profile = profiles[idx]
    dlg = QDialog(gui)
    dlg.setWindowTitle(f"Edit Trainee: {profile['name']}")
    form = QFormLayout(dlg)

    # Show name (read-only)
    name_edit = QLineEdit(profile['name']); name_edit.setReadOnly(True)
    form.addRow("Name:", name_edit)

    # Show analytics info
    analytics = profile.get('analytics', {})
    loss_reasons = analytics.get('loss_reasons', {})
    loss_str = ", ".join(f"{k.capitalize()}: {v}" for k,v in loss_reasons.items()) or "None"
    loss_lbl = QLineEdit(loss_str); loss_lbl.setReadOnly(True)
    form.addRow("Loss Reasons:", loss_lbl)

    clear_btn = QPushButton("Clear Analytics (Loss Reasons & Action Stats)")
    def clear_analytics():
        if QMessageBox.question(gui, "Confirm", "Clear all analytics for this profile?") == QMessageBox.StandardButton.Yes:
            profiles[idx]['analytics'] = {}
            save_profiles(profiles)
            # Reload profiles and reselect current trainee to update UI
            gui.profiles = load_profiles()
            gui.profile_select.setCurrentIndex(idx + 1)  # +1 for the 'Select Trainee' entry
            QMessageBox.information(gui, "Cleared", "Analytics cleared.")
            dlg.accept()
    clear_btn.clicked.connect(clear_analytics)
    form.addRow(clear_btn)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dlg.reject)
    form.addRow(buttons)
    dlg.exec()

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
    # Add Edit Profile button to main GUI if not already present
    if not hasattr(gui, 'edit_profile_btn'):
        gui.edit_profile_btn = QPushButton("Edit Trainee…")
        gui.edit_profile_btn.clicked.connect(lambda: show_edit_profile_dialog(gui))
        gui.main_layout.insertWidget(1, gui.edit_profile_btn)
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

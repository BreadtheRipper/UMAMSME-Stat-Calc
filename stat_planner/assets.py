import cv2
from pathlib import Path
from PyQt6.QtGui import QPixmap
from .settings import TEMPLATE_DIR, DIGIT_TEMPLATE_DIR, ICON_DIR, STATS

def load_templates():
    templates = {}
    for stat in STATS:
        path = TEMPLATE_DIR / f"{stat}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        templates[stat] = img
    return templates

def load_digit_templates():
    digit_templates = {}
    for d in range(10):
        path = DIGIT_TEMPLATE_DIR / f"{d}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        digit_templates[str(d)] = img
    return digit_templates

def load_stat_icons():
    icons = {}
    for stat in STATS:
        path = ICON_DIR / f"{stat}.png"
        if path.exists():
            icons[stat] = QPixmap(str(path))
        else:
            icons[stat] = None
    return icons


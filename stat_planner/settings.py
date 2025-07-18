from pathlib import Path

# === Paths ===
BASE_PATH           = Path(__file__).parent
TEMPLATE_DIR        = BASE_PATH / "assets" / "templates"
DIGIT_TEMPLATE_DIR  = BASE_PATH / "assets" / "digits"
ICON_DIR            = BASE_PATH / "assets" / "icons"
ICON_PATH           = ICON_DIR / "app_icon.ico"
PROFILES_FILE       = BASE_PATH / "profiles.json"
PHOTOS_DIR          = BASE_PATH / "assets" / "profiles"

# === Stats & thresholds ===
STATS                   = ["speed", "stamina", "power", "guts", "wit"]
FEEDBACK_WEIGHT         = 2
MATCH_THRESHOLD         = 0.4
DIGIT_MATCH_THRESHOLD   = 0.6

# --- Stat priority weights ---
# You can adjust these to change how much each priority level affects training suggestions
PRIORITY_WEIGHTS = {
    "Lowest": 0.5,
    "Low": 0.8,
    "Normal": 1.0,
    "High": 1.3,
    "Highest": 1.7
}
# This scale factor multiplies all weights (set to 1.0 for no scaling)
PRIORITY_WEIGHT_SCALE = 1.0

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
FEEDBACK_WEIGHT         = 5
MATCH_THRESHOLD         = 0.4
DIGIT_MATCH_THRESHOLD   = 0.6

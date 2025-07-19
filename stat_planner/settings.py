from pathlib import Path

# === Paths ===
BASE_PATH           = Path(__file__).parent
TEMPLATE_DIR        = BASE_PATH / "assets" / "templates"
DIGIT_TEMPLATE_DIR  = BASE_PATH / "assets" / "digits"
ICON_DIR            = BASE_PATH / "assets" / "icons"
ICON_PATH           = ICON_DIR / "app_icon.ico"
PROFILES_FILE       = BASE_PATH / "profiles.json"
PHOTOS_DIR          = BASE_PATH / "assets" / "profiles"

# === Screenshot Settings ===
GAME_EXE = "UmamusumePrettyDerby.exe"  # Changeable via future GUI


# === Stats & thresholds ===
STATS                   = ["speed", "stamina", "power", "guts", "wit"]
FEEDBACK_WEIGHT         = 2
MATCH_THRESHOLD         = 0.4
DIGIT_MATCH_THRESHOLD   = 0.6

# === Training Suggestion Weights ===
PRIORITY_WEIGHTS = {
    "Lowest": 0.5,
    "Low": 0.8,
    "Normal": 1.0,
    "High": 1.3,
    "Highest": 1.7
}
PRIORITY_WEIGHT_SCALE = 1.0  # Global scaling for priorities
LOSS_REASON_WEIGHT = 0.3     # Each loss increases stat weight by this factor

# Catch-up boost: applies when a stat is below this % of ideal
CATCHUP_THRESHOLD = 0.6        # 60% of ideal
CATCHUP_BOOST = 1.6            # 60% weight increase for lagging stats

# Overshoot penalty: applies when stat exceeds this % of ideal
OVERSHOOT_THRESHOLD = 0.85     # Start penalizing at 85% of ideal
OVERSHOOT_PENALTY_SCALE = 3    # Penalty multiplier for overtrained stats

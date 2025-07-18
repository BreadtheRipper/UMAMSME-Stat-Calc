import json
from pathlib import Path
from .settings import BASE_PATH

STATE_FILE = BASE_PATH / "run_state.json"

def save_state(state: dict):
    """
    state should be a JSON‑serializable dict containing:
      - profile_index (int)
      - ideal_stats (dict)
      - current_stats (dict)
      - history (list of dicts)
      - feedback_stat (str or None)
      - total_rounds (int)
      - rounds_done (int)
      - turns_left (int)
      - turn (int)
      - stat_priorities (dict, optional)
    """
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_state():
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)

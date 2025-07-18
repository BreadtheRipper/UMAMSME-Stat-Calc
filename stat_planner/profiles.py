import json
import shutil
from pathlib import Path
from .settings import BASE_PATH

PROFILES_FILE = BASE_PATH / "profiles.json"
PHOTOS_DIR    = BASE_PATH / "assets" / "profiles"

def load_profiles():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILES_FILE.exists():
        return []
    with open(PROFILES_FILE, "r") as f:
        return json.load(f)

def save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)

def add_profile(name, ideal_stats, photo_path=None):
    """
    - name: str
    - ideal_stats: dict of stat->int
    - photo_path: optional str path to image file
    """
    profiles = load_profiles()
    # Copy photo into assets/profiles if given
    dest_photo = None
    if photo_path:
        ext = Path(photo_path).suffix
        dest = PHOTOS_DIR / f"{name}{ext}"
        shutil.copy(photo_path, dest)
        dest_photo = str(dest.name)
    profiles.append({
        "name": name,
        "ideal_stats": ideal_stats,
        "photo": dest_photo
    })
    save_profiles(profiles)
    return profiles

def ensure_action_stats(profile):
    analytics = profile.setdefault("analytics", {})
    action_stats = analytics.setdefault("action_stats", {})
    for stat in profile["ideal_stats"]:
        action_stats.setdefault(stat, {
            "count": 0,
            "gains": {s: 0 for s in profile["ideal_stats"]}
        })
    return analytics

def record_action_gain(profile_index, action, prev_stats, new_stats):
    profiles = load_profiles()
    profile = profiles[profile_index]
    analytics = ensure_action_stats(profile)
    astats = analytics["action_stats"][action]
    astats["count"] += 1
    for s, new_v in new_stats.items():
        astats["gains"][s] += max(0, new_v - prev_stats.get(s, 0))
    save_profiles(profiles)

def record_feedback(profile_index, stat, loss=False):
    profiles = load_profiles()
    profile = profiles[profile_index]
    analytics = profile.setdefault("analytics", {})
    key = "loss_feedback" if loss else "optional_feedback"
    feedbacks = analytics.setdefault(key, {})
    feedbacks[stat] = feedbacks.get(stat, 0) + 1
    save_profiles(profiles)

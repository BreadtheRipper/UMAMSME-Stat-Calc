import cv2
import numpy as np
from .utils.screenshot import grab_game_screen  # adjust path as needed
from .settings import STATS, MATCH_THRESHOLD, DIGIT_MATCH_THRESHOLD
from .assets import load_templates, load_digit_templates

# Initialize once
stat_templates  = load_templates()
digit_templates = load_digit_templates()

def match_digits(region, debug=False, stat_name=""):
    found = []
    for digit, tmpl in digit_templates.items():
        res = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= DIGIT_MATCH_THRESHOLD)
        for pt in zip(*loc[::-1]):
            found.append((pt[0], res[pt[1], pt[0]], digit))
    if not found:
        return None
    # dedupe & pick highest scores
    found.sort(key=lambda x: (-x[1], x[0]))
    result, occupied = [], []
    for x, score, d in found:
        if not any(abs(x - ox) < 10 for ox in occupied):
            result.append((x, d))
            occupied.append(x)
    result.sort(key=lambda x: x[0])
    number = "".join(d for _, d in result)
    return int(number) if number.isdigit() and int(number) <= 1200 else None

def auto_read_stats(debug=False):
    screen = grab_game_screen()
    img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    detected = {}
    last_x = -1

    for stat in STATS:
        tmpl = stat_templates[stat]
        h, w = tmpl.shape
        search = gray if last_x < 0 else gray[:, last_x+1:]
        res = cv2.matchTemplate(search, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < MATCH_THRESHOLD:
            return None
        x = max_loc[0] + (last_x+1 if last_x>=0 else 0)
        y = max_loc[1]
        last_x = x

        # Define number region just right/below the header
        y1 = y + h + int(0.1*h)
        y2 = y1 + int(1.5*h)
        x1 = x + int(0.45*w)
        x2 = x + w - int(0.05*w)
        y2 = y2 - int(0.3*(y2-y1))
        region = gray[y1:y2, x1:x2]

        if debug:
            cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)

        num = match_digits(region, debug=debug, stat_name=stat)
        if num is None:
            return None
        detected[stat] = num

    if debug:
        cv2.imwrite("debug_template_boxes.png", img)
    return detected

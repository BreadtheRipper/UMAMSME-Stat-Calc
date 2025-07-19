import psutil
import pygetwindow as gw
from PIL import ImageGrab
from ..settings import GAME_EXE

def find_game_window(process_name):
    """
    Attempt to find the game window by matching process name or window title.
    """
    # Try to match window title
    for window in gw.getAllTitles():
        if process_name.lower().replace('.exe', '') in window.lower():
            try:
                w = gw.getWindowsWithTitle(window)[0]
                if w.isVisible:
                    print(f"[INFO] Found visible window: {w.title}")
                    return w
            except IndexError:
                continue

    # Check if process exists even if window isn’t visible
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                print(f"[INFO] Found process: {proc.info['name']}, but no visible window.")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None  # Nothing found

def grab_game_screen():
    """
    Capture a screenshot of the game window if possible, fallback to primary monitor.
    """
    window = find_game_window(GAME_EXE)
    if hasattr(window, 'box'):
        print(f"[INFO] Capturing game window: {window.title}")
        bbox = window.box  # (left, top, right, bottom)
        return ImageGrab.grab(bbox)
    elif window is True:
        print("[WARN] Process found but no visible window. Trying full display fallback.")
    else:
        print("[WARN] Game window/process not found. Falling back to primary monitor.")

    return ImageGrab.grab()

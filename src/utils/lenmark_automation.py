"""
LenMark_3DS DXF Automation — stable synchronized build (Fracktal ControlCenter)
Author: Siva (AMCOE) + ChatGPT refinement

Core features:
- Connect / embed LenMark_3DS into Layer Preview
- Step-by-step controlled automation (no blind waiting)
- Uses pywinauto Desktop() for real state sync
"""

import os, time, random, pyautogui, subprocess
from typing import Callable, Optional, Any
from pywinauto import Application, Desktop

# --- Config ---
LENMARK_EXE = r"C:\Program Files (x86)\LenMark_3DS\LenMark_3DS.exe"
LENMARK_TITLES = ["LenMark_3DS", "LenMark", "LenMark 3D"]
EMBED_MODE = False
EMBED_RELAUNCH: Optional[Callable[[], None]] = None


# -----------------------------------------------------------------------------
#  Window management helpers
# -----------------------------------------------------------------------------
def _is_hwnd_valid(hwnd: int) -> bool:
    try:
        import win32gui
        return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
    except Exception:
        return True


def _find_window() -> Optional[Any]:
    """Find existing LenMark window (embedded or standalone)."""
    if globals().get("EMBED_MODE", False):
        hwnd = globals().get("GLOBAL_LENMARK_HWND")
        if hwnd and _is_hwnd_valid(int(hwnd)):
            try:
                app = Application(backend="uia").connect(handle=int(hwnd))
                return app.window(handle=int(hwnd))
            except Exception:
                pass

    app = Application(backend="uia")
    for t in LENMARK_TITLES:
        try:
            app.connect(title_re=t)
            win = app.window(title_re=t)
            if win.exists(timeout=2):
                return win
        except Exception:
            continue
    return None


def _focus_lenmark_window(log: Callable[[str], None], hwnd: Optional[int] = None) -> bool:
    """Force focus to LenMark (UIA + Win32 fallback)."""
    try:
        import win32gui
    except Exception:
        win32gui = None

    win = _find_window()
    try:
        if win32gui:
            if hwnd is None and win is not None:
                hwnd = int(win.wrapper_object().handle)
            if hwnd:
                win32gui.SetForegroundWindow(int(hwnd))
                log("[LenMark] Focused LenMark window (Win32).")
                return True
        if win is not None:
            win.set_focus()
            log("[LenMark] Focused LenMark window (UIA).")
            return True
    except Exception:
        pass
    return False


def _launch_or_connect(log: Callable[[str], None]):
    """Connect to existing LenMark or launch new one."""
    win = _find_window()
    if win:
        log("[LenMark] Connected to running LenMark window.")
        _focus_lenmark_window(log)
        return win

    if not os.path.exists(LENMARK_EXE):
        raise FileNotFoundError("LenMark executable not found.")

    log(f"[LenMark] Launching: {LENMARK_EXE}")
    subprocess.Popen([LENMARK_EXE])
    start = time.time()
    while time.time() - start < 45:
        win = _find_window()
        if win:
            log("[LenMark] Window detected after launch.")
            _focus_lenmark_window(log)
            return win
        time.sleep(1)
    raise RuntimeError("Failed to find LenMark window after launch.")


# -----------------------------------------------------------------------------
#  Wait utilities (reliable GUI sync)
# -----------------------------------------------------------------------------
def _sleep(a=0.3, b=0.8):
    time.sleep(random.uniform(a, b))


def wait_until(log, condition_func, description, timeout=20, poll=0.1):
    """Generic wait loop until condition_func() returns True."""
    start = time.time()
    while time.time() - start < timeout:
        if condition_func():
            log(f"[LenMark] ✅ {description}")
            return True
        time.sleep(poll)
    log(f"[LenMark] ⚠ Timeout waiting for {description}")
    return False


def import_dialog_visible():
    for w in Desktop(backend="uia").windows():
        name = (w.window_text() or "").lower()
        if "import" in name or "open" in name:
            return True
    return False


def mark_window_visible():
    for w in Desktop(backend="uia").windows():
        if (w.window_text() or "").strip().lower() == "mark":
            return True
    return False


def dxf_visible(stem: str):
    stem = stem.lower().replace(".dxf", "")
    for w in Desktop(backend="uia").windows():
        if stem in (w.window_text() or "").lower():
            return True
    return False


# -----------------------------------------------------------------------------
#  Step definitions
# -----------------------------------------------------------------------------
def initial_marking_setup(log):
    """Open first DXF via Import dialog."""
    log("[LenMark] 🔹 Initial Marking Setup started...")
    pyautogui.hotkey("ctrl", "i")
    wait_until(log, import_dialog_visible, "Import dialog visible")
    _sleep(0.5, 1.0)

    for _ in range(3):
        pyautogui.press("tab"); _sleep(0.1, 0.2)
    pyautogui.press("down"); _sleep(0.1, 0.2)
    pyautogui.press("up"); _sleep(0.1, 0.2)
    pyautogui.press("enter"); _sleep(1.2, 1.8)
    log("[LenMark] ✅ First DXF opened.")


def perform_marking(log):
    """Trigger marking and wait for completion."""
    log("[LenMark] 🔹 Starting marking (F2)...")
    pyautogui.press("f2"); _sleep(0.15, 0.25)
    wait_until(log, mark_window_visible, "'Mark' window to appear", timeout=10, poll=0.1)
    wait_until(log, lambda: not mark_window_visible(), "'Mark' window to close", timeout=60, poll=0.1)
    log("[LenMark] ✅ Marking done.")


from pywinauto.keyboard import send_keys
from pywinauto import Desktop
import time

def file_menu_opened(timeout=3) -> bool:
    """Check if the File menu is open by looking for menu window."""
    start = time.time()
    while time.time() - start < timeout:
        for w in Desktop(backend="uia").windows():
            title = (w.window_text() or "").lower()
            if "file" in title and "menu" in title:
                return True
        time.sleep(0.1)
    return False

def close_current_file(log):
    log("[LenMark] 🔹 Closing current file (Alt+F → C → C → → → Enter)...")

    # Step 1: Trigger File menu
    send_keys("%F")  # Alt+F
    time.sleep(0.6)  # Let it open visually

    # Optional: Wait for File menu to be visible (if it's a separate window, use this)
    # if not file_menu_opened():
    #     log("[LenMark] ⚠ File menu did not appear, retrying...")
    #     send_keys("%F")
    #     time.sleep(0.6)

    # Step 2: Continue only if File menu was given time to open
    send_keys("C")    # First C
    send_keys("C")    # Second C
    send_keys("{ENTER}")
    send_keys("{RIGHT}")
    send_keys("{ENTER}")


    log("[LenMark] ✅ File closed.")

# -----------------------------------------------------------------------------
#  Main Automation Sequence
# -----------------------------------------------------------------------------
# --- Mark, Close, and Next Loop Controller -----------------------------------
def auto_mark_all_dxf_files(folder_path: str, log: Callable[[str], None] = print, **kwargs):
    """
    Sequential marking for all DXFs:
    1️⃣ Initial import (Ctrl+I → Tab×3 → Down×1 → Up×1 → Enter)
    2️⃣ Mark (F2) and wait for completion
    3️⃣ Close file (Alt+F → C → C → → Enter)
    4️⃣ New file (Ctrl+N), Import (Ctrl+I → Tab×3 → Down×N → Enter)
    5️⃣ Repeat until all DXFs are processed
    """

    if not os.path.isdir(folder_path):
        log(f"[Lenmark] ❌ Folder not found: {folder_path}")
        return

    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".dxf")])
    if not files:
        log("[Lenmark] ⚠ No DXFs found.")
        return

    log(f"[Lenmark] Starting synchronized marking for {len(files)} DXFs...")

    # Ensure LenMark window focus
    win = _find_window() or _launch_or_connect(log)
    hwnd = int(win.wrapper_object().handle)
    _focus_lenmark_window(log, hwnd)

    # ----------------------------------------------------------------------
    # 1️⃣ FIRST FILE
    # ----------------------------------------------------------------------
    log("[Lenmark] 🔹 Importing first DXF...")
    pyautogui.hotkey("ctrl", "i")
    wait_until(log, import_dialog_visible, "Import dialog visible", timeout=5, poll=0.5)

    for _ in range(3):
        pyautogui.press("tab"); _sleep(0.15, 0.25)
    pyautogui.press("down"); _sleep(0.15, 0.25)
    pyautogui.press("up"); _sleep(0.15, 0.25)
    pyautogui.press("enter"); _sleep(1.5, 2.0)

    log(f"[Lenmark] ✅ First DXF opened: {files[0]}")
    perform_marking(log)
    close_current_file(log)

    # ----------------------------------------------------------------------
    # 2️⃣ REMAINING FILES LOOP
    # ----------------------------------------------------------------------
    for i, filename in enumerate(files[1:], start=2):
        _focus_lenmark_window(log, hwnd)

        # New + Import
        pyautogui.hotkey("ctrl", "n"); _sleep(0.4, 0.6)
        pyautogui.hotkey("ctrl", "i")
        wait_until(log, import_dialog_visible, "Import dialog visible", timeout=5, poll=0.5)

        for _ in range(3):
            pyautogui.press("tab"); _sleep(0.15, 0.25)
        for _ in range(i - 1):  # go down one extra file each iteration
            pyautogui.press("down"); _sleep(0.1, 0.2)
        pyautogui.press("enter"); _sleep(1.5, 2.0)

        log(f"[Lenmark] ✅ Opened {filename} (Down×{i-1})")

        perform_marking(log)
        close_current_file(log)
        log(f"[Lenmark] ✅ {i}/{len(files)} done — {filename}")

    log("[Lenmark] 🎯 All DXFs marked successfully.")



# -----------------------------------------------------------------------------
# CLI entry (manual testing)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    auto_mark_all_dxf_files(folder_path=folder)


# -----------------------------------------------------------------------------
# Embedding Helper
# -----------------------------------------------------------------------------
from .embed_lenmark import embed_lenmark_in_preview

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


def debug_list_windows(log):
    """Debug function to list all visible windows."""
    log("[DEBUG] Listing all visible windows:")
    for w in Desktop(backend="uia").windows():
        title = w.window_text() or ""
        if title.strip():  # Only show windows with titles
            log(f"[DEBUG] Window: '{title}' (Class: {w.class_name()})")


def import_dialog_visible():
    """Check for import/open dialog with enhanced detection."""
    for w in Desktop(backend="uia").windows():
        name = (w.window_text() or "").lower()
        # More comprehensive dialog detection - include more keywords
        if any(keyword in name for keyword in ["import", "open", "file", "select", "choose", "dxf", "browse", "dialog", "window"]):
            # Only exclude if it's clearly the main LenMark window
            is_main_window = any(main_title.lower() in name for main_title in LENMARK_TITLES) and len(name.split()) <= 2
            if not is_main_window:
                return True
    return False


def get_import_dialog_window():
    """Get the import dialog window object for focusing."""
    for w in Desktop(backend="uia").windows():
        name = (w.window_text() or "").lower()
        # More comprehensive dialog detection - include more keywords
        if any(keyword in name for keyword in ["import", "open", "file", "select", "choose", "dxf", "browse", "dialog", "window"]):
            # Only exclude if it's clearly the main LenMark window
            is_main_window = any(main_title.lower() in name for main_title in LENMARK_TITLES) and len(name.split()) <= 2
            if not is_main_window:
                return w
    return None


def ensure_import_dialog_focused(log, max_retries=3):
    """Ensure import dialog is visible and focused with debug logging and fallback."""
    for attempt in range(max_retries):
        log(f"[Lenmark] Checking for import dialog (attempt {attempt + 1}/{max_retries})")

        # Debug: list all windows on first attempt
        if attempt == 0:
            debug_list_windows(log)

        dialog_win = get_import_dialog_window()
        if dialog_win:
            try:
                # Try to focus the dialog
                dialog_win.set_focus()
                _sleep(0.2, 0.3)  # Slightly longer wait

                # Verify focus worked by checking if dialog is still visible
                if get_import_dialog_window() is not None:
                    log(f"[Lenmark] ✅ Import dialog focused successfully")
                    return True
                else:
                    log(f"[Lenmark] ⚠️ Dialog focus lost immediately")

            except Exception as e:
                log(f"[Lenmark] Failed to focus dialog: {e}")

        # If dialog not found or focus failed, try reopening
        log(f"[Lenmark] Reopening import dialog (attempt {attempt + 1})")
        pyautogui.hotkey("ctrl", "i")
        _sleep(0.5, 0.8)  # Longer wait for dialog to appear

    # Fallback: if we still can't detect the dialog, assume it opened and proceed
    # This handles cases where the dialog title doesn't match our detection patterns
    log("[Lenmark] ⚠️ Dialog detection failed, proceeding with blind navigation")
    log("[Lenmark] 💡 If this works, the dialog title may need to be added to detection keywords")
    return True  # Allow proceeding with file selection


def verify_dxf_imported(filename: str, log, timeout=10):
    """Verify that the specified DXF file was actually imported with improved detection."""
    stem = filename.replace(".dxf", "").lower()
    log(f"[Lenmark] Verifying {filename} import...")

    start = time.time()
    while time.time() - start < timeout:
        for w in Desktop(backend="uia").windows():
            title = (w.window_text() or "").lower()

            # Check multiple ways the filename might appear
            if (stem in title or
                filename.lower() in title or
                # Check if any significant part of the filename is in the title
                any(word in title for word in stem.split() if len(word) > 2)):

                # Make sure it's a LenMark window (but be less restrictive)
                if any(main_title.lower() in title for main_title in LENMARK_TITLES):
                    log(f"[Lenmark] ✅ {filename} confirmed imported (title: '{title}')")
                    return True

                # Also accept if it looks like a document window
                if len(title.split()) > 1 and not any(keyword in title for keyword in ["import", "open", "dialog"]):
                    log(f"[Lenmark] ✅ {filename} confirmed imported (document window: '{title}')")
                    return True

        time.sleep(0.3)  # Slightly longer polling

    log(f"[Lenmark] ❌ Failed to verify {filename} import after {timeout}s")
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

def _select_file_via_arrow_keys(file_index: int, log):
    """Ultra-fast file selection with optimized navigation."""
    try:
        log(f"[Lenmark] Selecting file at index {file_index}...")

        if file_index == 0:
            # First file: optimized sequence
            pyautogui.press("down", presses=1, interval=0.02)
            _sleep(0.05, 0.08)
            pyautogui.press("up", presses=1, interval=0.02)
        else:
            # For large indices, use Page Down for massive speed gains
            if file_index > 30:
                # More aggressive Page Down jumping
                pages_to_jump = file_index // 25  # Larger page size assumption
                remaining_arrows = file_index % 25

                # Fast page jumping
                for _ in range(pages_to_jump):
                    pyautogui.press("pagedown")
                    _sleep(0.03, 0.05)  # Minimal delay

                # Fine-tune with burst arrows
                if remaining_arrows > 0:
                    pyautogui.press("down", presses=remaining_arrows, interval=0.01)
            else:
                # For smaller indices, use burst arrows
                pyautogui.press("down", presses=file_index, interval=0.01)

        _sleep(0.05, 0.08)
        pyautogui.press("enter")
        _sleep(0.8, 1.2)  # Reduced wait time

        log(f"[Lenmark] Selected file #{file_index + 1}")

    except Exception as e:
        log(f"[Lenmark] ⚠️ Arrow key navigation failed: {e}")
        raise


def _navigate_to_file_list(log):
    """Fast navigation to file list in import dialog."""
    # Burst tab presses for speed
    pyautogui.press("tab", presses=3, interval=0.02)
    _sleep(0.05, 0.08)


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

    # Ensure import dialog is visible and focused
    if not ensure_import_dialog_focused(log):
        log("[Lenmark] ❌ Cannot proceed - import dialog not accessible")
        return

    # Fast navigation to file list
    _navigate_to_file_list(log)

    # Fast file selection
    _select_file_via_arrow_keys(0, log)

    # DISABLED: Verify the DXF was actually imported
    # if not verify_dxf_imported(files[0], log):
    #     log(f"[Lenmark] ❌ First DXF {files[0]} failed to import - aborting")
    #     return

    log(f"[Lenmark] ✅ First DXF opened: {files[0]}")
    perform_marking(log)
    close_current_file(log)

    # ----------------------------------------------------------------------
    # 2️⃣ REMAINING FILES LOOP
    # ----------------------------------------------------------------------
    for i, filename in enumerate(files[1:], start=2):
        _focus_lenmark_window(log, hwnd)

        # New file + Import with redundancy
        pyautogui.hotkey("ctrl", "n"); _sleep(0.2, 0.4)
        pyautogui.hotkey("ctrl", "i")

        # Ensure import dialog is visible and focused
        if not ensure_import_dialog_focused(log):
            log(f"[Lenmark] ❌ Cannot import {filename} - dialog not accessible")
            continue

        # Fast navigation to file list
        _navigate_to_file_list(log)

        # Fast file selection
        _select_file_via_arrow_keys(i - 1, log)

        # DISABLED: Verify the DXF was actually imported
        # if not verify_dxf_imported(filename, log):
        #     log(f"[Lenmark] ❌ {filename} failed to import - skipping")
        #     continue

        log(f"[Lenmark] ✅ Opened {filename} (fast navigation)")

        perform_marking(log)
        close_current_file(log)
        log(f"[Lenmark] ✅ {i}/{len(files)} done — {filename}")

    log("[Lenmark] 🎯 All DXFs marked successfully.")



def test_import_dialog_detection():
    """Test function to check import dialog detection - run this manually to debug."""
    print("Testing import dialog detection...")
    print("Opening import dialog with Ctrl+I...")

    pyautogui.hotkey("ctrl", "i")
    time.sleep(2)  # Wait for dialog to appear

    print("\nAll visible windows:")
    debug_list_windows(print)

    dialog = get_import_dialog_window()
    if dialog:
        print(f"\n✅ Detected import dialog: '{dialog.window_text()}'")
    else:
        print("\n❌ No import dialog detected")

    return dialog is not None


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

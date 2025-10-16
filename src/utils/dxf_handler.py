"""DXF folder selection and listing helper.

Provides a single function:
    select_and_list_dxf_files(main_window, log_signal) -> tuple[str | None, list[str]]

Requirements implemented (per spec):
 1. Opens a native folder picker (QFileDialog.getExistingDirectory).
 2. On selection:
      - Saves folder to main_window.input_dir
      - Collects *.dxf (case-insensitive) files (non-recursive, files only)
      - Natural numeric sort (img_01, img_2, img_10)
 3. Logs via log_signal.emit(str):
        📂 Selected folder: <path>
        📄 Found N DXF files.
        - filename1.dxf
        - filename2.dxf
 4. If no DXF files: warning popup + log: "❌ No DXF files found".
 5. Updates GUI text box main_window.home_screen.processModeBox (QTextEdit / QPlainTextEdit)
        📂 Folder: <folder path>
        📄 Total DXF Files: N
        🧾 Files:
          - file1.dxf
          - file2.dxf
 6. Shows QMessageBox.information popup (success) or warning (no files).
 7. Returns (folder_path, list_of_absolute_file_paths) or (None, []).
 8. Handles all exceptions gracefully, logging errors.

Notes:
 - Natural sort implemented via regex digit tokenization.
 - Returns absolute file paths for convenience; UI/log use just basenames.
 - If user cancels dialog, returns (None, []) and logs cancellation.
"""
from __future__ import annotations

from typing import List, Tuple
import os
import re

try:  # Import lazily to avoid issues in non-GUI contexts
    from PyQt5.QtWidgets import QFileDialog, QMessageBox, QTextEdit, QPlainTextEdit
    from PyQt5.QtCore import QObject
except Exception:  # pragma: no cover - GUI libs may be absent during certain tests
    QFileDialog = QMessageBox = QTextEdit = QPlainTextEdit = object  # type: ignore
    QObject = object  # type: ignore

__all__ = [
    "select_and_list_dxf_files",
    "load_and_display_dxf_folder",
    "show_dxf_summary_in_process_mode",
    "display_dxf_summary_in_process_mode",
]

def _natural_key(name: str):
    """Return a key for natural sorting (splitting digits)."""
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", name)]

def _emit(log_signal, message: str):
    """Safely emit a log line if log_signal has emit(); otherwise ignore."""
    if log_signal is None:
        return
    try:
        emit = getattr(log_signal, "emit", None)
        if callable(emit):
            emit(message)
        elif callable(log_signal):  # fallback if passed a callable directly
            log_signal(message)
    except Exception:
        pass

def select_and_list_dxf_files(main_window, log_signal) -> Tuple[str | None, List[str]]:
    """Open a folder picker, list .dxf files, update UI and return selection.

    Parameters
    ----------
    main_window : object
        Main window instance expected to have attributes:
          - input_dir (read/write) optional
          - home_screen.processModeBox (QTextEdit/QPlainTextEdit)
    log_signal : pyqtSignal(str) or object with emit(str) or callable
        Used for logging text messages.

    Returns
    -------
    (folder_path, dxf_files): tuple[str | None, list[str]]
        folder_path is None if selection canceled or error; dxf_files are absolute paths.
    """
    # Determine starting directory heuristic
    start_dir = None
    try:
        start_dir = getattr(main_window, "input_dir", None)
    except Exception:
        start_dir = None
    if not start_dir or not os.path.isdir(start_dir):
        # Try to locate project dxf input; fallback to HOME
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.abspath(os.path.join(here, os.pardir, "dxf_to_emd", "input"))
            start_dir = candidate if os.path.isdir(candidate) else os.path.expanduser("~")
        except Exception:
            start_dir = os.path.expanduser("~")

    # Open native folder picker
    try:
        folder = QFileDialog.getExistingDirectory(main_window, "Select DXF Folder", start_dir)  # type: ignore[attr-defined]
    except Exception as e:
        _emit(log_signal, f"❌ Failed to open folder dialog: {e}")
        return (None, [])

    # User canceled
    if not folder:
        _emit(log_signal, "[DXF] Folder selection canceled.")
        return (None, [])

    if not os.path.isdir(folder):
        _emit(log_signal, f"❌ Selected path is not a directory: {folder}")
        try:
            QMessageBox.warning(main_window, "DXF Load", "Selected path is not a directory.")  # type: ignore[attr-defined]
        except Exception:
            pass
        return (None, [])

    # Persist selected directory
    try:
        setattr(main_window, "input_dir", folder)
    except Exception:
        pass

    # Enumerate DXF files (non-recursive)
    try:
        entries = os.listdir(folder)
    except Exception as e:
        _emit(log_signal, f"❌ Failed to list directory: {e}")
        try:
            QMessageBox.warning(main_window, "DXF Load", f"Failed to list directory: {e}")  # type: ignore[attr-defined]
        except Exception:
            pass
        return (None, [])

    dxf_names = []
    for name in entries:
        full_path = os.path.join(folder, name)
        if os.path.isfile(full_path) and name.lower().endswith(".dxf"):
            dxf_names.append(name)

    dxf_names.sort(key=_natural_key)
    dxf_paths = [os.path.join(folder, n) for n in dxf_names]

    # Logging
    _emit(log_signal, f"📂 Selected folder: {folder}")
    if dxf_names:
        _emit(log_signal, f"📄 Found {len(dxf_names)} DXF file{'s' if len(dxf_names) != 1 else ''}.")
        for n in dxf_names:
            _emit(log_signal, f"- {n}")
    else:
        _emit(log_signal, "❌ No DXF files found")

    # Update processModeBox
    try:
        process_box = getattr(getattr(main_window, "home_screen", None), "processModeBox", None)
    except Exception:
        process_box = None

    if process_box is not None:
        try:
            lines = [
                f"📂 Folder: {folder}",
                f"📄 Total DXF Files: {len(dxf_names)}"
            ]
            if dxf_names:
                lines.append("🧾 Files:")
                lines.extend([f"  - {n}" for n in dxf_names])
            text = "\n".join(lines)
            if hasattr(process_box, "setPlainText"):
                process_box.setPlainText(text)
            else:  # Fallback (e.g., QLabel or other widget mistakenly assigned)
                try:
                    process_box.setText(text)  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception as e:
            _emit(log_signal, f"⚠️ Failed to update process box: {e}")

    # Popups
    try:
        if dxf_names:
            QMessageBox.information(main_window, "DXF Files Loaded", f"{len(dxf_names)} DXF files found in folder")  # type: ignore[attr-defined]
        else:
            QMessageBox.warning(main_window, "DXF Files", "No DXF files found in the selected folder.")  # type: ignore[attr-defined]
    except Exception:
        pass

    if not dxf_names:
        return (folder, [])  # return folder anyway; may aid user to see path

    return (folder, dxf_paths)


def load_and_display_dxf_folder(main_window, log_signal) -> Tuple[str | None, List[str]]:
    """Open a folder dialog, log DXF file discovery, update Process Mode box, and return results.

    Behavior (per spec):
      - Native folder picker (QFileDialog.getExistingDirectory)
      - On selection: save folder to main_window.input_dir
      - Collect *.dxf files (case-insensitive, non-recursive, files only)
      - Natural numeric sort (img_01, img_2, img_10)
      - Log format:
            📂 DXF folder selected → <path>
            📄 Found N DXF files:
                - file1.dxf
                - file2.dxf
        (If none: log "❌ No DXF files found.")
      - Update main_window.home_screen.processModeBox with:
            📂 Folder: <folder>
            📄 Total DXF Files: N
            🧾 File List:
            - file1.dxf
            - file2.dxf
      - Popup: QMessageBox.information("Loaded N DXF files from <folder>") or warning if none.
      - Return (folder_path, [absolute_paths]) else (None, []).

    Parameters
    ----------
    main_window : object
        Expected to expose input_dir and home_screen.processModeBox.
    log_signal : pyqtSignal(str) | object with .emit(str) | callable
        Logging sink; messages emitted via .emit if present else callable.
    """
    # Resolve starting directory
    try:
        start_dir = getattr(main_window, "input_dir", None)
    except Exception:
        start_dir = None
    if not start_dir or not os.path.isdir(start_dir):
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.abspath(os.path.join(here, os.pardir, "dxf_to_emd", "input"))
            start_dir = candidate if os.path.isdir(candidate) else os.path.expanduser("~")
        except Exception:
            start_dir = os.path.expanduser("~")

    # Open dialog
    try:
        folder = QFileDialog.getExistingDirectory(main_window, "Select DXF Folder", start_dir)  # type: ignore
    except Exception as e:
        _emit(log_signal, f"❌ Folder dialog failed: {e}")
        return (None, [])

    # User cancel
    if not folder:
        _emit(log_signal, "[DXF] Folder selection canceled.")
        return (None, [])
    if not os.path.isdir(folder):
        _emit(log_signal, f"❌ Invalid folder path: {folder}")
        try:
            QMessageBox.warning(main_window, "DXF Load", "Invalid folder path selected.")  # type: ignore
        except Exception:
            pass
        return (None, [])

    # Persist folder
    try:
        setattr(main_window, "input_dir", folder)
    except Exception:
        pass

    # Enumerate DXF files
    try:
        entries = os.listdir(folder)
    except Exception as e:
        _emit(log_signal, f"❌ Failed to read directory: {e}")
        try:
            QMessageBox.warning(main_window, "DXF Load", f"Failed to read directory: {e}")  # type: ignore
        except Exception:
            pass
        return (None, [])

    dxf_names: List[str] = []
    for name in entries:
        path = os.path.join(folder, name)
        if os.path.isfile(path) and name.lower().endswith(".dxf"):
            dxf_names.append(name)
    dxf_names.sort(key=_natural_key)
    dxf_paths = [os.path.join(folder, n) for n in dxf_names]

    # Logging
    _emit(log_signal, f"📂 DXF folder selected → {folder}")
    if dxf_names:
        _emit(log_signal, f"📄 Found {len(dxf_names)} DXF files:")
        for n in dxf_names:
            _emit(log_signal, f"    - {n}")
    else:
        _emit(log_signal, "❌ No DXF files found.")

    # Update Process Mode text box
    try:
        process_box = getattr(getattr(main_window, "home_screen", None), "processModeBox", None)
    except Exception:
        process_box = None
    if process_box is not None:
        lines = [
            f"📂 Folder: {folder}",
            f"📄 Total DXF Files: {len(dxf_names)}",
            "🧾 File List:",
        ]
        if dxf_names:
            lines.extend([f"- {n}" for n in dxf_names])
        else:
            lines.append("(none)")
        text = "\n".join(lines)
        try:
            if hasattr(process_box, "setPlainText"):
                process_box.setPlainText(text)
            else:
                process_box.setText(text)  # type: ignore
        except Exception as e:
            _emit(log_signal, f"⚠️ Failed to update Process Mode box: {e}")

    # Popups + post-confirm summary injection
    try:
        if dxf_names:
            QMessageBox.information(main_window, "DXF Files", f"Loaded {len(dxf_names)} DXF files from {folder}")  # type: ignore
            # After user clicks OK, refresh Process Mode box via dedicated helper
            try:
                # Preferred new helper name per latest spec
                display_dxf_summary_in_process_mode(main_window, folder, dxf_paths)
            except Exception as e:
                _emit(log_signal, f"⚠️ Failed updating Process Mode summary: {e}")
        else:
            QMessageBox.warning(main_window, "DXF Files", "No DXF files found.")  # type: ignore
    except Exception:
        # Even if popup fails, still attempt to update the Process Mode box
        try:
            display_dxf_summary_in_process_mode(main_window, folder, dxf_paths)
        except Exception:
            pass

    if not dxf_names:
        return (folder, [])
    return (folder, dxf_paths)


def show_dxf_summary_in_process_mode(main_window, folder: str, dxf_files: List[str]) -> None:
    """Update the Process Mode box with a formatted DXF summary.

    Format:
        📂 Folder: <folder>
        📄 Total DXF Files: N
        🧾 File List:
        - file1.dxf
        - file2.dxf

    If the processModeBox widget doesn't exist, a warning is printed.

    Parameters
    ----------
    main_window : object
        Must expose home_screen.processModeBox (QTextEdit / QPlainTextEdit / QLabel).
    folder : str
        Folder path selected.
    dxf_files : List[str]
        Absolute file paths (already sorted). Basenames will be displayed.
    """
    try:
        home_screen = getattr(main_window, "home_screen", None)
    except Exception:
        home_screen = None
    process_box = None
    if home_screen is not None:
        try:
            process_box = getattr(home_screen, "processModeBox", None)
        except Exception:
            process_box = None

    basenames = [os.path.basename(p) for p in dxf_files]
    lines = [
        f"📂 Folder: {folder}",
        f"📄 Total DXF Files: {len(basenames)}",
        "🧾 File List:",
    ]
    if basenames:
        lines.extend([f"- {name}" for name in basenames])
    else:
        lines.append("(none)")
    text = "\n".join(lines)

    if process_box is None:
        # Fallback logging
        try:
            print("[DXF] Warning: processModeBox not found; cannot display summary.")
        except Exception:
            pass
        return

    try:
        if hasattr(process_box, "setPlainText"):
            process_box.setPlainText(text)
        else:
            process_box.setText(text)  # type: ignore[attr-defined]
    except Exception as e:
        try:
            print(f"[DXF] Failed to update Process Mode summary: {e}")
        except Exception:
            pass


def display_dxf_summary_in_process_mode(main_window, folder: str, dxf_files: List[str]) -> None:
    """New helper (spec-requested) to update Process Mode box with DXF summary immediately.

    This mirrors show_dxf_summary_in_process_mode but keeps the requested function name.
    If both exist, this one is treated as canonical and show_dxf_summary_in_process_mode
    may internally delegate here in future refactors.

    Parameters
    ----------
    main_window : object
        Expects main_window.home_screen.processModeBox widget.
    folder : str
        Selected DXF folder path.
    dxf_files : List[str]
        Absolute DXF file paths (sorted). Basenames displayed.
    """
    try:
        home_screen = getattr(main_window, "home_screen", None)
    except Exception:
        home_screen = None

    target_widget = None
    process_box = None
    log_box = None
    if home_screen is not None:
        # Prefer processModeBox
        try:
            process_box = getattr(home_screen, "processModeBox", None)
        except Exception:
            process_box = None
        # Secondary option: automationLogText
        try:
            log_box = getattr(home_screen, "automationLogText", None)
        except Exception:
            log_box = None
    target_widget = process_box if process_box is not None else log_box

    # Build plain summary (per latest spec request):
    # Folder path, total file count, then list of filenames.
    basenames = [os.path.basename(p) for p in dxf_files]
    lines = [
        f"Folder: {folder}",
        f"Total DXF Files: {len(basenames)}",
        "Files:",
    ]
    if basenames:
        lines.extend([f" - {n}" for n in basenames])
    else:
        lines.append(" (none)")
    summary_text = "\n".join(lines)

    if target_widget is None:
        # Attempt log via controller's signal, else print
        try:
            ctrl = getattr(main_window, "process_automation_controller", None)
            msg = "[DXF] Warning: No widget (processModeBox/automationLogText) available for DXF summary display." 
            if ctrl and hasattr(ctrl, "automation_log_signal"):
                ctrl.automation_log_signal.emit(msg)
            else:
                print(msg)
        except Exception:
            pass
        return

    try:
        # Clear previous content if possible
        if hasattr(target_widget, "clear"):
            try:
                target_widget.clear()
            except Exception:
                pass

        # Prefer append line-by-line if widget supports append (e.g., QTextEdit)
        if hasattr(target_widget, "append"):
            try:
                for line in lines:
                    target_widget.append(line)
                return
            except Exception:
                # Fall back to setPlainText
                pass

        if hasattr(target_widget, "setPlainText"):
            target_widget.setPlainText(summary_text)
        elif hasattr(target_widget, "setText"):
            target_widget.setText(summary_text)  # type: ignore[attr-defined]
        else:
            # Last resort: attempt write attribute
            try:
                target_widget.write(summary_text)  # type: ignore[attr-defined]
            except Exception:
                # Give up silently; log via controller if available
                raise RuntimeError("No suitable method to set text on target widget")
    except Exception as e:
        try:
            ctrl = getattr(main_window, "process_automation_controller", None)
            if ctrl and hasattr(ctrl, "automation_log_signal"):
                ctrl.automation_log_signal.emit(f"[DXF] Failed to update DXF summary widget: {e}")
            else:
                print(f"[DXF] Failed to update DXF summary widget: {e}")
        except Exception:
            pass

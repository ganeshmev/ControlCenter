import sys
import os
import time

# Expose the embedded LenMark HWND for automation reuse
GLOBAL_LENMARK_HWND = None  # type: ignore[assignment]



def embed_lenmark_in_preview(container_widget, log=print):
    """
    Fully launch and embed the LenMark_3DS main render/document window inside the given PyQt5 widget.
    - Launch from the exact path (not a shortcut)
    - Wait up to 15s for the top-level render/document window (title filter)
    - Verify process via psutil if available (continue with warning otherwise)
    - Strip decorations, SetParent, MoveWindow to fill, and track resize
    - Clear logs with ✅/❌; Windows-only guard
    """
    if os.name != 'nt':
        log('❌ [LenMark] Embedding only supported on Windows.')
        return
    try:
        import win32gui, win32con, win32process
        import subprocess
        from PyQt5.QtCore import QEvent, QObject
        # Optional psutil import via importlib to avoid static linter errors
        import importlib, importlib.util
        psutil = None  # type: ignore
        try:
            if importlib.util.find_spec('psutil') is not None:
                psutil = importlib.import_module('psutil')
            else:
                log('⚠️ [LenMark] psutil not installed; skipping strict process-name verification.')
        except Exception:
            psutil = None
            log('⚠️ [LenMark] psutil import failed; continuing without it.')
        # Signal embedding mode to the automation module so it skips external MoveWindow
        try:
            lenmark_automation = importlib.import_module('utils.lenmark_automation')
            setattr(lenmark_automation, 'EMBED_MODE', True)
            # Provide a relaunch hook to allow re-embedding if automation needs it
            def _relaunch():
                embed_lenmark_in_preview(container_widget, log)
            setattr(lenmark_automation, 'EMBED_RELAUNCH', _relaunch)
        except Exception:
            # If not available, continue; embedding will still work
            pass
    except ImportError as e:
        log(f'❌ [LenMark] Import error: {e}')
        return
    LENMARK_EXE = r"C:\Program Files (x86)\LenMark_3DS\LenMark_3DS.exe"
    # 1. Kill any stray LenMark_3DS.exe processes first
    killed = 0
    if psutil:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                exe_path = proc.info.get('exe')
                name = (proc.info.get('name') or '').lower()
                if exe_path and os.path.normcase(exe_path) == os.path.normcase(LENMARK_EXE):
                    proc.kill(); killed += 1
                elif not exe_path and name == 'lenmark_3ds.exe':
                    proc.kill(); killed += 1
            except Exception:
                continue
    else:
        # Best-effort fallback without psutil
        try:
            subprocess.run(['taskkill', '/IM', 'LenMark_3DS.exe', '/F'], capture_output=True)
        except Exception:
            pass
    if killed:
        log(f'⚠️ [LenMark] Terminated {killed} stray LenMark_3DS.exe process(es) before relaunch.')
    # 2. Launch the real executable
    try:
        log('[LenMark] Launching...')
        proc = subprocess.Popen([LENMARK_EXE])
    except Exception as e:
        log(f'❌ [LenMark] Failed to launch LenMark_3DS: {e}')
        return
    # 3. Wait up to 15s for a window with correct process and title
    hwnd = None
    pid = proc.pid
    def _is_target_title(title: str) -> bool:
        # Must include 'LenMark_3DS' and either 'Document' or a dash
        t = (title or '')
        tl = t.lower()
        return ('lenmark_3ds' in tl) and (('document' in tl) or (' - ' in t) or ('–' in t))

    def _find_hwnd():
        result = []
        def _enum_handler(h, _):
            if not win32gui.IsWindowVisible(h):
                return
            title = win32gui.GetWindowText(h)
            if not _is_target_title(title):
                return
            try:
                _, win_pid = win32process.GetWindowThreadProcessId(h)
            except Exception:
                return
            if win_pid != pid:
                return
            # Optional strict verification via psutil
            if psutil:
                try:
                    pname = (psutil.Process(win_pid).name() or '').lower()
                    if pname != 'lenmark_3ds.exe':
                        return
                except Exception:
                    pass
            result.append(h)
        win32gui.EnumWindows(_enum_handler, None)
        return result[0] if result else None
    for _ in range(30):
        hwnd = _find_hwnd()
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        log('❌ [LenMark] Window not found / failed to attach (15s timeout).')
        return
    log(f'✅ [LenMark] Found LenMark_3DS render/document window HWND={hwnd}')
    # 4. Remove window decorations
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | win32con.WS_SYSMENU)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
        log('✅ [LenMark] Window decorations removed.')
    except Exception as e:
        log(f'❌ [LenMark] Failed to remove decorations: {e}')
    # 5. Reparent to container
    try:
        container_hwnd = int(container_widget.winId())
        win32gui.SetParent(hwnd, container_hwnd)
        log(f'✅ [LenMark] Set parent to container HWND={container_hwnd}')
    except Exception as e:
        log(f'❌ [LenMark] Failed to reparent: {e}')
        return
    # Store global handle for automation module
    try:
        global GLOBAL_LENMARK_HWND
        GLOBAL_LENMARK_HWND = int(hwnd)
        # Also mirror into lenmark_automation if available
        import importlib
        lenmark_automation = importlib.import_module('utils.lenmark_automation')
        setattr(lenmark_automation, 'GLOBAL_LENMARK_HWND', GLOBAL_LENMARK_HWND)
        log(f'✅ [LenMark] Stored embedded HWND={GLOBAL_LENMARK_HWND} for automation reuse')
    except Exception:
        pass
    # 6. Resize to fit container and track resize
    def _resize_embedded():
        try:
            rect = container_widget.rect()
            w, h = rect.width(), rect.height()
            win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
            log(f'✅ [LenMark] Embedded window resized to {w}x{h}')
        except Exception as e:
            log(f'❌ [LenMark] Resize error: {e}')
    _resize_embedded()
    class _ResizeFilter(QObject):
        def eventFilter(self, obj, ev):
            if obj is container_widget and ev.type() == QEvent.Resize:
                _resize_embedded()
            return False
    _filter = _ResizeFilter(container_widget)
    container_widget.installEventFilter(_filter)
    # Keep a reference to prevent GC of the filter
    setattr(container_widget, '_lenmark_resize_filter', _filter)
    log('✅ Embedded successfully')

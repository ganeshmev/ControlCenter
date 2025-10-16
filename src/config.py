class Config:
    DEVELOPMENT_MODE = True  # Set to False in production
    # Path to LenMark_3DS executable (update as needed)
    LENMARK_EXE_PATH = r"C:\Program Files (x86)\LenMark_3DS\LenMark_3DS.exe"
    # Main window title or regex for LenMark/Feeltek app
    # Used as a regex by automation (title_re). You can keep it specific, we'll also try fallbacks below.
    LENMARK_MAIN_TITLE = "LenMark_3DS"
    # Additional title regex patterns to try when connecting (order matters)
    LENMARK_CONNECT_TITLE_PATTERNS = [
        LENMARK_MAIN_TITLE,
        r".*(LenMark|Feeltek).*",
        r".*(Laser|Mark).*",
        r"LenMark.*",
        r".*3DS.*",
    ]
    # Expected dialog titles/controls (best-effort defaults; override if different)
    LENMARK_IMPORT_MENU = "&File"
    LENMARK_IMPORT_ACTION = "&Import DXF"
    LENMARK_MARK_BUTTON_TEXT = "&Mark"
    LENMARK_OPEN_DIALOG_TITLE = "Open"
    # Menu sequences for layer reset
    LENMARK_CLOSE_ALL_SEQUENCE = "%F C A"  # Alt+F, then 'C' Close submenu, then 'A' All (example; adjust)
    LENMARK_NEW_SEQUENCE = "^n"  # Ctrl+N for New

    # Demo behavior: if Mark button is disabled (no hardware/license), skip clicking Mark
    DEMO_SKIP_MARK_IF_DISABLED = True

    # Launch robustness
    LENMARK_LAUNCH_RETRIES = 5
    LENMARK_LAUNCH_RETRY_DELAY_SEC = 5

    # DXF selection rules
    LENMARK_DXF_MIN_SIZE_BYTES = 1024  # only consider files > 1 KB
    LENMARK_ALWAYS_PICK_FIRST_VALID = True  # always pick the first valid DXF (> min size) regardless of layer index

    # Open dialog / import robustness
    LENMARK_OPEN_DIALOG_TIMEOUT_SEC = 20
    LENMARK_OPEN_CONFIRM_RETRIES = 3
    LENMARK_USE_FULL_PATH_FALLBACK = True
    LENMARK_IMPORT_OPTIONS_TIMEOUT_SEC = 20  # time to wait for import options/confirmation dialog
    # Fallback key sequences to open Import/Open dialog if Ctrl+I doesn't work
    # These are sent via pywinauto.send_keys in order until a dialog is detected
    LENMARK_IMPORT_KEY_SEQUENCES = [
        "^i",                   # Ctrl+I (Import)
        "^o",                   # Ctrl+O (Open)
        "%F o {ENTER}",         # Alt+F, O, Enter (Open)
        "%F i {ENTER}",         # Alt+F, I, Enter (Import)
        "%F {DOWN}{DOWN}{ENTER}" # Alt+F, Down, Down, Enter (navigate menu)
    ]
    # Optional Win32 menu paths to open Import/Open via menu_select
    LENMARK_MENU_IMPORT_PATHS = [
        "&File->&Import",
        "&File->&Open",
        "File->Import",
        "File->Open",
        "File->Open...",
        "&File->Open...",
        "&File->Import DXF",
        "File->Import DXF",
    ]

    # Optional AutomationIds for stable selectors (fill using Inspect.exe if available)
    LENMARK_MARK_BUTTON_AUTOMATION_ID = None  # e.g., "markButton"
    LENMARK_STATUS_BAR_AUTOMATION_ID = None   # e.g., "statusBar"
    LENMARK_OPEN_FILE_EDIT_AUTOMATION_ID = None  # e.g., "1148"
    LENMARK_OPEN_FILE_OPEN_BUTTON_AUTOMATION_ID = None  # e.g., "1"
    
    # Fixed DXF input directory (optional). If enabled, UI will always use this folder
    # and automation will expect DXFs to be copied here before each print.
    # Choose a simple path without spaces/special characters to avoid Open dialog quirks.
    LENMARK_DXF_USE_FIXED_DIR = True
    LENMARK_DXF_FIXED_DIR = r"C:\\LenmarkDXF"
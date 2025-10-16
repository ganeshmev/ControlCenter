# ControlCenter DXF Automation

This project integrates DXF automation for LenMark_3DS using `pywinauto`.

## Prerequisites

- Windows
- Python 3.9+
- Dependencies:

```powershell
pip install -r requirements.txt
```

## Configure LenMark_3DS

Edit `src/config.py`:

- `LENMARK_EXE_PATH`: Full path to LenMark_3DS.exe
- `LENMARK_MAIN_TITLE`: Main window title/regex
- Menu sequences and dialog titles:
	- `LENMARK_CLOSE_ALL_SEQUENCE` (e.g., `%F C A`)
	- `LENMARK_NEW_SEQUENCE` (e.g., `^n`)
	- `LENMARK_OPEN_DIALOG_TITLE` (e.g., `Open`)
- Demo mode:
	- `DEMO_SKIP_MARK_IF_DISABLED = True` skips clicking Mark when hardware/license is not present
- Optional AutomationIds (recommended for robustness):
	- `LENMARK_MARK_BUTTON_AUTOMATION_ID`
	- `LENMARK_STATUS_BAR_AUTOMATION_ID`
	- `LENMARK_OPEN_FILE_EDIT_AUTOMATION_ID`
	- `LENMARK_OPEN_FILE_OPEN_BUTTON_AUTOMATION_ID`

## Finding AutomationIds with Inspect.exe

1. Install Windows SDK or download **Inspect.exe** from Microsoft.
2. Run Inspect.exe as admin.
3. Hover over the LenMark_3DS controls:
	 - Mark button
	 - Status bar (if any)
	 - Open dialog: file name edit, Open button
4. Note the `AutomationId` for each and update `src/config.py` accordingly.

## Using the UI

1. Launch the app
2. On Home Screen, set `Process Mode` to `DXF (Automation)`
3. Click `Upload directory` and choose the folder that contains all DXF layers
4. Start the print

Per layer, the app will:
- Close All
- New
- Import the i-th DXF from the sorted list in the selected directory
- Click Mark (if enabled; skipped in demo)

A small log area on Home Screen shows automation steps and status.

## Troubleshooting

- If the Open dialog, Mark button, or titles differ from defaults, set the AutomationIds and titles in `src/config.py`.
- If Mark is disabled during development, enable `DEMO_SKIP_MARK_IF_DISABLED` to skip clicking.
- For flaky selectors, prefer AutomationIds over names or titles.
# PyQt 3D Printer Application

Version of GUI which is currently being used now

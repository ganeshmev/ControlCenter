import argparse
import os
import sys
from pathlib import Path

# Ensure imports work when running from src/
THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
WORKSPACE_DIR = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.lenmark_automation import test_launch, run_dxf_mark  # type: ignore
from config import Config  # type: ignore

def find_default_dxf() -> str | None:
    # Look for a DXF under workspace dxf_to_emd/input
    dxf_dir = WORKSPACE_DIR / "dxf_to_emd" / "input"
    if not dxf_dir.exists():
        return None
    candidates = sorted([p for p in dxf_dir.glob("*.dxf") if p.is_file()])
    return str(candidates[0]) if candidates else None
def main():
    parser = argparse.ArgumentParser(description="LenMark_3DS automation test runner")
    parser.add_argument("--launch-only", action="store_true", help="Only test launching/connecting the app")
    parser.add_argument("--file", type=str, help="Path to DXF file to import and mark")
    parser.add_argument("--exe", type=str, default=Config.LENMARK_EXE_PATH, help="Path to LenMark_3DS.exe")
    args = parser.parse_args()

    if args.launch_only:
        print("[TEST] Launch/connect only...")
        ok = test_launch(exe_path=args.exe)
        print("[TEST] RESULT:", ok)
        sys.exit(0 if ok else 2)

    dxf = args.file or find_default_dxf()
    if not dxf:
        print("[TEST] No DXF file provided and none found in dxf_to_emd/input")
        sys.exit(1)
    if not os.path.isfile(dxf):
        print(f"[TEST] DXF does not exist: {dxf}")
        sys.exit(1)

    print(f"[TEST] Running DXF mark for: {dxf}")
    try:
        run_dxf_mark(dxf_file_path=dxf, exe_path=args.exe, log_cb=lambda m: print(m))
        print("[TEST] DXF mark completed.")
        sys.exit(0)
    except Exception as e:
        print(f"[TEST] DXF mark failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()

import os
import re
import tkinter as tk
from tkinter import filedialog

def clean_filename(filename):
    # Convert to lowercase
    filename = filename.lower()

    # Remove leading zeros from numbers using regex
    filename = re.sub(r'(\D)0+(\d)', r'\1\2', filename)

    return filename

def rename_emd_files(folder_path):
    renamed_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(".emd"):
                old_path = os.path.join(root, filename)
                new_filename = clean_filename(filename)
                new_path = os.path.join(root, new_filename)

                # Rename only if filename changes
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {old_path} -> {new_path}")
                else:
                    print(f"No change: {old_path}")

                renamed_files.append(new_filename)

    return renamed_files

def check_missing_files(files):
    numbers = []

    # Extract numbers from filenames like img_1.emd
    for f in files:
        match = re.search(r'(\d+)\.emd$', f)
        if match:
            numbers.append(int(match.group(1)))

    if not numbers:
        print("⚠️ No numbered .emd files found to check sequence.")
        return

    numbers.sort()
    missing = []
    for expected in range(numbers[0], numbers[-1] + 1):
        if expected not in numbers:
            missing.append(expected)

    if missing:
        print(f"\n❌ Missing files detected: {missing}")
    else:
        print("\n✅ All files are in proper sequence with no missing numbers!")

def main():
    # Open folder browse dialog
    root = tk.Tk()
    root.withdraw()  # Hide the tkinter window
    folder_selected = filedialog.askdirectory(title="Select Folder Containing EMD Files")

    if folder_selected:
        renamed_files = rename_emd_files(folder_selected)
        check_missing_files(renamed_files)
        print("\n✅ Process completed: lowercase, removed leading zeros, and sequence checked.")
    else:
        print("No folder selected.")

if __name__ == "__main__":
    main()

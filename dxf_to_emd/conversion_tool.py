import time
import subprocess
from networkx import add_path
import pyautogui
import os
import glob
from datetime import datetime
import easygui

# Define file paths
# input_directory = r"D:\AMCOE project\format_conversion\input"
# output_directory = r"D:\AMCOE project\format_conversion\output emd files"

input_directory = easygui.diropenbox(title="Select Input Folder")
output_directory = easygui.diropenbox(title="Select Output Folder")

print(f"Input: {input_directory}")
print(f"Output: {output_directory}")
# Ensure output directory exists
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Fetch all DXF files in the directory
dxf_files = glob.glob(os.path.join(input_directory, "*.dxf"))

if not dxf_files:
    pyautogui.alert("No DXF files found in the directory.", "Error")
    exit()

# Ask the user how many files they want to convert
num_files_to_convert = pyautogui.prompt(f"How many files do you want to convert (max {len(dxf_files)} files)?", "File Conversion", len(dxf_files))

try:
    num_files_to_convert = int(num_files_to_convert)
except ValueError:
    pyautogui.alert("Invalid input! Please enter a valid number.")
    exit()

# Limit to available files
num_files_to_convert = min(num_files_to_convert, len(dxf_files))

# Start timing the entire process
start_time = datetime.now()

# Step 1: Launch LenMark_3DS.exe ONCE
# subprocess.Popen(add_path)
# time.sleep(3)  # Wait for the application to open
# Step 1: Launch LenMark_3DS.exe ONCE
lenmark_path = "C:\Program Files (x86)\LenMark_3DS\LenMark_3DS.exe"  # <-- change this to the real path
subprocess.Popen([lenmark_path])
time.sleep(3)  # Wait for the application to open


for i in range(num_files_to_convert):
    # Close the application after each file
    pyautogui.hotkey("alt", "f4")
    time.sleep(2)

    # **Handle "Save Changes?" Dialog**
    pyautogui.press("right")  # Move selection to "No" (if "Yes" is default)
    time.sleep(0.5)

    pyautogui.press("enter")  # Confirm exit without saving changes
    time.sleep(2)  # Allow time for LenMark_3DS to fully close

    subprocess.Popen(lenmark_path)
    time.sleep(3)  # Wait for the application to open
    input_file = dxf_files[i]
    file_name = os.path.basename(input_file)
    output_file = os.path.join(output_directory, file_name.replace(".dxf", ".emd"))

    print(f"Processing {i + 1}/{num_files_to_convert}: {file_name}")

   # Step 2: Open "Import" option (using Ctrl + I)
    pyautogui.hotkey("ctrl", "i")
    time.sleep(1)

    # **Step 2.1: Close any open file dialogs before proceeding** (new fix)
    pyautogui.hotkey("esc")  # Press Escape to close any leftover dialogs
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "i")  # Reopen the Import dialog
    time.sleep(1)

    # Step 3: Navigate to File Name field
    for _ in range(4):
        pyautogui.hotkey("shift", "tab")
        time.sleep(0.03)

# Step 4: Enter the full file pathC:\Users\AswinN\Desktop\Files\img_003.dxf

    # pyautogui.hotkey("alt", "d")  # Selects the address bar
    # time.sleep(0.5)

    # Step 4A: Navigate to Input Directory
    pyautogui.hotkey("ctrl", "l")  # Focus on address bar (Alt+D also works in some cases)  
    time.sleep(0.5)
    pyautogui.write(input_directory)  # Type the correct input directory
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(1)

    # Step 4B: Enter the file name (not full path)
    pyautogui.write(os.path.basename(input_file))  # Type only the filename
    time.sleep(1)
    pyautogui.press("enter")  # Open the file
    time.sleep(2)  # Allow time for the file to load

    # Step 5: Save as .emd format
    pyautogui.hotkey("ctrl", "s")
    time.sleep(3)

    # Step 6: Enter the output file path
    pyautogui.hotkey("alt", "d")  # Selects the address bar
    time.sleep(0.5)
    # Step 6A: Navigate to Output Directory

    pyautogui.hotkey("ctrl", "l")  # Focus on address bar
    time.sleep(0.5)
    pyautogui.write(output_directory)  # Type the correct output directory
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(1)

    # Step 6B: Enter the file name (not full path)
    pyautogui.write(os.path.basename(output_file))  # Only enter filename, since we're in the right folder
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)  # Allow time for save

    # Step 6.5: Wait for file to be created (max 3 seconds)
    file_save_start_time = time.time()
    while not os.path.exists(output_file):
        if time.time() - file_save_start_time > 3:
            pyautogui.alert(f"Failed to save {file_name}. Skipping.", "Error")
            break
        time.sleep(1)

    print(f"File saved: {output_file}")

    time.sleep(2)  # Allow time for LenMark_3DS to reset


    # Handle file overwrite prompt (if needed)
    pyautogui.press("right")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    
     # **Press 'Delete' key after handling overwrite**
    pyautogui.press("delete")
    time.sleep(1)  # Ensure smooth transition
    

# Step 7: Close the application after all files are processed
pyautogui.hotkey("alt", "f4")

# Final notification after all files are processed
total_time = datetime.now() - start_time
pyautogui.alert(f"Conversion completed for {num_files_to_convert} files!\nTotal Time: {total_time}", "Batch Conversion Complete")
print(f"All files processed in {total_time}")

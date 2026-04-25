import subprocess
import sys

result = subprocess.run(
    ["taskkill", "/F", "/IM", "ffplay.exe", "/T"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("Audio stopped.")
else:
    print("Nothing playing.")

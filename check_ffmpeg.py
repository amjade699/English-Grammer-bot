import subprocess

try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg found!")
    print(result.stdout.split('\n')[0])
except FileNotFoundError:
    print("FFmpeg NOT found in PATH (WinError 2)")
except Exception as e:
    print(f"An error occurred: {e}")

#!python
import math
import os
import subprocess
import glob
import argparse
import tempfile
from datetime import datetime
from datetime import timedelta
import shutil
import time

start = time.perf_counter()
# Get the user's temp directory
temp_dir = tempfile.gettempdir()
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Get temp directory and full path
temp_dir = tempfile.gettempdir()
log_filename = os.path.join(temp_dir, "video_convert", f"my_command_output_{timestamp}.log")
os.makedirs(os.path.dirname(log_filename), exist_ok=True)

# === STEP 0: Parse arguments ===
parser = argparse.ArgumentParser(description="Create a slideshow video from images and audio.")
parser.add_argument("--audio", required=True, help="Path to the audio file (e.g., audio.mp3)")
#parser.add_argument("--mode", choices=["split", "fixed"], required=True, help="Duration mode: 'split' or 'fixed'")
parser.add_argument("--frame-duration", type=float, help="Duration per image (used in 'fixed' mode)")
parser.add_argument("--video-duration", default="auto", help="Total video duration in seconds or 'auto' (used in 'split' mode)")
parser.add_argument("--images", help="Folder containing image files (default: 'images')")
parser.add_argument("--output", default="slideshow.mp4", help="Output video filename (default: 'slideshow.mp4')")

args = parser.parse_args()

audio_file = args.audio
#mode = args.mode.lower()
image_folder = args.images
output_video = args.output

if not os.path.exists(args.audio):
    print(f"❌ Error: File not found at {args.audio}")
    exit(1)

if args.images and not os.path.isdir(args.images):
    print(f"❌ Error: Path not found at {args.images}")
    exit(1)

if not os.path.isdir(os.path.dirname(log_filename)):
    print(f"❌ Error: Unable to create directory for log {os.path.dirname(log_filename)}")
    exit(1)

if not shutil.which("ffmpeg"):
    print("❌ Error: ffmpeg is not installed")
    exit(1)

# === STEP 1: Get all image files ===
image_files = sorted(glob.glob(os.path.join(image_folder, "*.jpg"))) if image_folder else None
if not image_files:
    print(f"❌ Error: No Valid image files supplied from --@ {image_folder}")
    exit(1)

def log_console(result):
    with open(log_filename, "a") as logfile:
       logfile.write(result.stdout)
       logfile.write(result.stderr)

# === STEP 2: Get audio duration ===
def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-i", audio_path,
        "-show_entries", "format=duration",
        "-v", "quiet",
        "-of", "csv=p=0"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    log_console(result)
    return float(result.stdout.strip())

audio_duration = get_audio_duration(audio_file)

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

if args.video_duration.lower() == "auto" or not is_float(args.video_duration):
   total_video_duration = float(audio_duration)
else:
   total_video_duration = float(args.video_duration)

# === STEP 3: Determine duration per image ===
if args.frame_duration and is_float(args.frame_duration):
   duration_per_image = float(args.frame_duration)
else:
   duration_per_image = total_video_duration / len(image_files)

# === STEP 4: Create video clips from images ===
temp_clips = []
num_slots = math.ceil(total_video_duration / duration_per_image)

for i in range(num_slots):
    img = image_files[i % len(image_files)]  # Loop back to start if needed
    temp_name = f"clip_{i}.mp4"
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-t", str(duration_per_image),
        "-i", img, "-vf", "scale=1280:720", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", temp_name
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    log_console(result)
    temp_clips.append(temp_name)


# === STEP 5: Create concat list file ===
with open("concat_list.txt", "w") as f:
    for clip in temp_clips:
        f.write(f"file '{clip}'\n")

# === STEP 6: Concatenate clips ===
result = subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "concat_list.txt", "-c", "copy", "slideshow_raw.mp4"
], capture_output=True, text=True)
log_console(result)

# === STEP 7: Add audio ===
final_audio_duration = min(audio_duration, total_video_duration)
result = subprocess.run([
    "ffmpeg", "-y", "-i", "slideshow_raw.mp4", "-i", audio_file,
    "-c:v", "copy", "-c:a", "aac", "-shortest", output_video
], capture_output=True, text=True)
log_console(result)

def format_seconds(seconds):
    return str(timedelta(seconds=int(seconds)))

# === CLEANUP ===
for clip in temp_clips:
    os.remove(clip)
os.remove("concat_list.txt")
os.remove("slideshow_raw.mp4")
end = time.perf_counter()
print(f"✅ {format_seconds(total_video_duration)} duration Video Converteds Successfully @{output_video}")
print(f"✅ Process took {format_seconds(end-start)}")

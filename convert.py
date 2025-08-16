import math
import os
import subprocess
import glob
import argparse

# === STEP 0: Parse arguments ===
parser = argparse.ArgumentParser(description="Create a slideshow video from images and audio.")
parser.add_argument("--audio", required=True, help="Path to the audio file (e.g., audio.mp3)")
#parser.add_argument("--mode", choices=["split", "fixed"], required=True, help="Duration mode: 'split' or 'fixed'")
parser.add_argument("--frame-duration", type=float, help="Duration per image (used in 'fixed' mode)")
parser.add_argument("--video-duration", default="auto", help="Total video duration in seconds or 'auto' (used in 'split' mode)")
parser.add_argument("--images", default="images", help="Folder containing image files (default: 'images')")
parser.add_argument("--output", default="slideshow.mp4", help="Output video filename (default: 'slideshow.mp4')")

args = parser.parse_args()

audio_file = args.audio
#mode = args.mode.lower()
image_folder = args.images
output_video = args.output

# === STEP 1: Get all image files ===
image_files = sorted(glob.glob(os.path.join(image_folder, "*.jpg")))
if not image_files:
    raise Exception(f"No .jpg images found in folder: {image_folder}")

# === STEP 2: Get audio duration ===
def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-i", audio_path,
        "-show_entries", "format=duration",
        "-v", "quiet",
        "-of", "csv=p=0"
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    subprocess.run(cmd)
    temp_clips.append(temp_name)


# === STEP 5: Create concat list file ===
with open("concat_list.txt", "w") as f:
    for clip in temp_clips:
        f.write(f"file '{clip}'\n")

# === STEP 6: Concatenate clips ===
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "concat_list.txt", "-c", "copy", "slideshow_raw.mp4"
])

# === STEP 7: Add audio ===
final_audio_duration = min(audio_duration, total_video_duration)
subprocess.run([
    "ffmpeg", "-y", "-i", "slideshow_raw.mp4", "-i", audio_file,
    "-c:v", "copy", "-c:a", "aac", "-shortest", output_video
])

# === CLEANUP ===
for clip in temp_clips:
    os.remove(clip)
os.remove("concat_list.txt")
os.remove("slideshow_raw.mp4")

print(f"✅ Slideshow video created: {output_video}")

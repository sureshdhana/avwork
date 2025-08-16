import argparse
from scipy.signal import butter, lfilter
import numpy as np
import soundfile as sf
from moviepy import AudioFileClip, VideoFileClip

def design_high_pass(cutoff=300, fs=16000, order=4):
    nyquist = 0.5 * fs
    norm_cutoff = cutoff / nyquist
    b, a = butter(order, norm_cutoff, btype='high', analog=False)
    return b, a

def apply_high_pass(data, cutoff=300, fs=16000, order=4):
    b, a = design_high_pass(cutoff, fs, order)
    return lfilter(b, a, data)

def main():
    parser = argparse.ArgumentParser(description="Apply wind noise filter to slideshow audio.")
    parser.add_argument("input_video", help="Path to input slideshow video file")
    parser.add_argument("--cutoff", type=int, default=300, help="High-pass filter cutoff frequency (Hz)")
    parser.add_argument("--output", default="slideshow_filtered.mp4", help="Output video file name")
    args = parser.parse_args()

    # Extract audio
    clip = VideoFileClip(args.input_video)
    audio = clip.audio
    audio.write_audiofile("temp_audio.wav")

    # Apply wind filter
    data, fs = sf.read("temp_audio.wav")
    filtered = apply_high_pass(data, cutoff=args.cutoff, fs=fs)
    sf.write("filtered_audio.wav", filtered, fs)

    # Reattach filtered audio
    filtered_audio = AudioFileClip("filtered_audio.wav")
    final_clip = clip.set_audio(filtered_audio)
    final_clip.write_videofile(args.output, codec="libx264", audio_codec="aac")

if __name__ == "__main__":
    main()

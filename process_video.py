import yt_dlp
import os
import subprocess
import sys

BAD_APPLE_LINK = "https://youtu.be/FtutLA63Cp8?si=5XTK8B9r6dqfhr50"
OUTPUT_MP4 = "bad_apple.mp4"
FRAME_DIR = "frames"

if len(sys.argv) < 5:
    print("How to use: python3 process_video.py <WIDTH> <HEIGHT> <FPS> <DITHER_TYPE>")
    print("Example: python3 process_video.py 96 48 12 o8x8")
    print("DITHER_TYPE: 'o8x8' (sorted dithering) or 'none' (threshold)")
    sys.exit(1)

WIDTH = int(sys.argv[1])
HEIGHT = int(sys.argv[2])
FPS = int(sys.argv[3])
DITHER = sys.argv[4]

# --- 1. Download do Vídeo ---
if not os.path.exists(OUTPUT_MP4):
    print(f"Downloading Bad Apple ({BAD_APPLE_LINK})...")
    ydl_opts = {
        'outtmpl': OUTPUT_MP4,
        'format': 'mp4[height<=480]/bestvideo+bestaudio/best',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([BAD_APPLE_LINK])
        print("Downloaded")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        sys.exit(1)
else:
    print(f"[=] {OUTPUT_MP4} already exists, skipping download.")

script_path = "process_frames.sh"
pack_script_name = "pack_frames.py"

script = f"""#!/bin/bash
set -e

VIDEO="../{OUTPUT_MP4}"
OUTDIR="{FRAME_DIR}"
WIDTH={WIDTH}
HEIGHT={HEIGHT}
FPS={FPS}
DITHER="{DITHER}"              
THRESHOLD="50%"                

mkdir -p "$OUTDIR"
cd "$OUTDIR"

echo "Extracting frames (${{WIDTH}}x${{HEIGHT}} @${{FPS}} fps)..."
ffmpeg -y -i "$VIDEO" -vf "scale=${{WIDTH}}:${{HEIGHT}}:flags=lanczos,fps=${{FPS}}" -r ${{FPS}} frame_%04d.png

echo "Converting to PBM (monocromatic 1-bit) with DITHER='${{DITHER}}'..."
for f in frame_*.png; do
  if [ "$DITHER" = "none" ]; then
    convert "$f" -colorspace Gray -threshold "$THRESHOLD" -depth 1 "${{f%.png}}.pbm"
  else
    convert "$f" -colorspace Gray -ordered-dither "$DITHER" -depth 1 "${{f%.png}}.pbm"
  fi
  rm "$f" # op: remove PNG
done

echo "Conversion done!"
"""

with open(script_path, "w") as f:
    f.write(script)

os.chmod(script_path, 0o755)
print(f"Generated: {script_path}")

print(f"Executing {script_path}...")
try:
    subprocess.run(["./" + script_path], check=True)
    print(f"{script_path} is done executing!")

    print(f"Executing python3 {pack_script_name} {WIDTH} {HEIGHT} {FPS}...")
    subprocess.run(["python3", pack_script_name, str(WIDTH), str(HEIGHT), str(FPS)], check=True) # <- change here python3 with python or py if you need
    print("Generated .rle e .h!")

except subprocess.CalledProcessError as e:
    print(f"Failed to exec a command. Error code: {e.returncode}")
    print("Make sure you have 'ffmpeg' and 'imagemagick' (command 'convert') installed.")
    sys.exit(1)
except FileNotFoundError:
    print(f"The file {pack_script_name} was not found. Are you in the same directory?.")
    sys.exit(1)

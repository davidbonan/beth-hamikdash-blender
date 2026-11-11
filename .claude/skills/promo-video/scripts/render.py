"""Render a clip from its folder (storyboard.json + media): -14 LUFS, X-ready MP4, contact sheet.

    python3 render.py promo/clips/<date>-<name> [--draft]

Outputs promo/finals/<date>-<name>.mp4 (promo/drafts/ with --draft) and <clip>/contact.png.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from env import PROMO, ROOT

STUDIO = Path(__file__).resolve().parent.parent / "studio"
BRAND_FILES = {"mark.svg": ROOT / "site" / "favicon.svg"}
LOUDNESS = "I=-14:TP=-1:LRA=11"
PEAK_LIMIT = 0.79
SHEET_FRAMES = 48


def copy_brand(clip):
    (clip / "brand").mkdir(exist_ok=True)
    for name, source in BRAND_FILES.items():
        shutil.copyfile(source, clip / "brand" / name)


def render(clip, draft, work):
    raw = work / "raw.mp4"
    options = ["--scale", "0.5", "--crf", "28"] if draft else ["--crf", "16"]
    if os.environ.get("REMOTION_BROWSER"):
        options += ["--browser-executable", os.environ["REMOTION_BROWSER"]]
    subprocess.run(["npx", "remotion", "render", "src/index.ts", "Clip", str(raw), f"--props={clip / 'storyboard.json'}",
                    f"--public-dir={clip}", "--codec", "h264", "--enforce-audio-track", "--audio-bitrate", "320k", "--log", "error", *options],
                   cwd=STUDIO, check=True)
    return raw


def normalize_loudness(raw, output):
    measure = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", f"loudnorm={LOUDNESS}:print_format=json", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    measured = json.loads(re.findall(r"\{[^{}]+\}", measure)[-1])
    if measured["input_i"] == "-inf":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-c", "copy", "-movflags", "+faststart", output], check=True)
        return
    second_pass = (f"loudnorm={LOUDNESS}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
                   f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
                   f"offset={measured['target_offset']}:linear=true,alimiter=limit={PEAK_LIMIT}:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", second_pass, "-ar", "48000", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", output], check=True)


def loudness_of(video):
    summary = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128=peak=true", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    integrated = re.findall(r"I:\s+(-?[\d.]+) LUFS", summary)[-1]
    peaks = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    return f"{integrated} LUFS, peak {peaks[-1]} dBTP" if peaks else "silent"


def duration_of(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True, check=True).stdout)


def contact_sheet(video, output):
    rate = SHEET_FRAMES / duration_of(video)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps={rate},scale=320:-2,tile=6x8",
                    "-frames:v", "1", output], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("clip", type=Path)
    parser.add_argument("--draft", action="store_true", help="half resolution, fast, to judge pacing")
    args = parser.parse_args()
    clip = args.clip.resolve()
    copy_brand(clip)
    destination = PROMO / ("drafts" if args.draft else "finals")
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{clip.name}.mp4"
    with tempfile.TemporaryDirectory() as work:
        normalize_loudness(render(clip, args.draft, Path(work)), output)
    print(output, "·", loudness_of(output), f"· {output.stat().st_size / 1e6:.1f} MB")
    sheet = clip / "contact.png"
    contact_sheet(output, sheet)
    print(sheet)


if __name__ == "__main__":
    main()

"""Music track on elevenlabs.io (Music v2.5), built from a track file cut into sections.

    python3 music.py --track <clip>/music.txt --out-dir <clip>/music [--takes 2] [--dry-run]
                     [--reference <audio> --window 1-31 --strength medium]

`--reference` conditions every section on 11 to 30 s of a recording (a known melody, a style); the window is uploaded once.

Track file: `styles:` / `avoid:` / `voice:` lines, then one `[name | seconds | direction]` header per section, followed by
its sung lines if any (a line in Latin letters is sung, a line in Hebrew letters is the reader's and is not sent); `#` comments.
Without sung lines, `voice:` is a wordless vocalise; with them, it describes the singers and a section without lines is instrumental.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

from env import api_key

API_URL = "https://api.elevenlabs.io/v1/music"
MODEL = "music_v2_5"
OUTPUT_FORMAT = "mp3_48000_192"
CREDITS_PER_SECOND = 12.5
TIMEOUT_S = 900

UNITY_STYLES = ["one continuous piece, same theme throughout"]
REJECTED_STYLES = ["spoken words", "tempo change", "genre change"]
INSTRUMENTAL_STYLES = ["instrumental only"]
REJECTED_VOICE_STYLES = ["vocals", "singing", "humming", "choir"]
VOCALISE_STYLES = ["wordless vocalise, vowels only, no words", "same voice from start to end"]
MAX_SECTIONS, MAX_LINES, MAX_LINE_CHARS = 28, 30, 200
HEBREW_LETTER = re.compile("[א-ת]")
SECTION_MS, TOTAL_MS = (3000, 120000), 600000
REFERENCE_WINDOW_MS = (11000, 30000)
UPLOADS = "references.json"
GLOBAL_KEYS = ("styles", "avoid", "voice")


@dataclass
class Section:
    name: str
    duration_ms: int
    direction: str | None
    lines: list[str]


@dataclass
class Track:
    styles: list[str]
    avoided: list[str]
    voice: list[str]
    sections: list[Section]

    @property
    def duration_ms(self):
        return sum(section.duration_ms for section in self.sections)

    @property
    def is_sung(self):
        return any(section.lines for section in self.sections)

    def voicing(self, section):
        if section.lines:
            return "sung"
        return "vocalise" if self.voice and not self.is_sung else "instrumental"

    def positive_styles(self, section):
        voicing = {"sung": self.voice, "vocalise": self.voice + VOCALISE_STYLES,
                   "instrumental": INSTRUMENTAL_STYLES}[self.voicing(section)]
        return self.styles + voicing + UNITY_STYLES + ([section.direction] if section.direction else [])

    def negative_styles(self, section):
        voicing = self.voicing(section)
        lyrics = [] if voicing == "sung" else ["lyrics"]
        voices = REJECTED_VOICE_STYLES if voicing == "instrumental" else []
        return REJECTED_STYLES + lyrics + voices + self.avoided


def read_track(path):
    globals_, sections = {}, []
    with open(path, encoding="utf-8") as file:
        for number, line in enumerate(file, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            header = re.fullmatch(r"\[(.+)\]", line)
            key_value = re.fullmatch(rf"({'|'.join(GLOBAL_KEYS)})\s*:\s*(.+)", line)
            if header:
                name, duration, direction = ([field.strip() for field in header[1].split("|")] + [""] * 2)[:3]
                if not duration:
                    raise SystemExit(f"{path}:{number}: missing duration in [{name}]")
                sections.append(Section(name, int(round(float(duration) * 1000)), direction or None, []))
            elif key_value and not sections:
                globals_[key_value[1]] = [style.strip() for style in key_value[2].split(",") if style.strip()]
            elif sections and not key_value:
                if not HEBREW_LETTER.search(line):
                    sections[-1].lines.append(line)
            else:
                raise SystemExit(f"{path}:{number}: expected `styles:` / `avoid:` / `voice:` before the sections, "
                                 f"a [name | seconds | direction] header or a sung line")
    return Track(globals_.get("styles", []), globals_.get("avoid", []), globals_.get("voice", []), sections)


def check(track):
    if not 1 <= len(track.sections) <= MAX_SECTIONS:
        raise SystemExit(f"{len(track.sections)} sections: 1 to {MAX_SECTIONS} allowed")
    for section in track.sections:
        if not 1 <= len(section.name) <= 100:
            raise SystemExit(f"Section name must be 1 to 100 characters: '{section.name}'")
        if not SECTION_MS[0] <= section.duration_ms <= SECTION_MS[1]:
            raise SystemExit(f"[{section.name}]: {section.duration_ms / 1000:g} s, a section lasts 3 to 120 s")
    lines = [line for section in track.sections for line in section.lines]
    if len(lines) > MAX_LINES:
        raise SystemExit(f"{len(lines)} sung lines: {MAX_LINES} at most")
    for line in lines:
        if len(line) > MAX_LINE_CHARS:
            raise SystemExit(f"Sung line over {MAX_LINE_CHARS} characters: '{line[:40]}…'")
    if track.duration_ms > TOTAL_MS:
        raise SystemExit(f"{track.duration_ms / 1000:g} s in total: 600 s at most")


def credits(duration_ms):
    return round(duration_ms / 1000 * CREDITS_PER_SECOND)


def composition_plan(track, conditioning):
    chunks = [{"text": "\n".join([f"[{section.name}]", *(section.lines or ([f"{{{section.direction}}}"] if section.direction else []))]),
               "duration_ms": section.duration_ms,
               "positive_styles": track.positive_styles(section),
               "negative_styles": track.negative_styles(section), **conditioning}
              for section in track.sections]
    return {"composition_plan": {"chunks": chunks}, "model_id": MODEL}


def conditioning(song_id, window, strength):
    return {"conditioning_ref": {"song_id": song_id, "range": {"start_ms": 0, "end_ms": window[1] - window[0]}},
            "condition_strength": strength}


def window_ms(text):
    start, end = (int(round(float(bound) * 1000)) for bound in text.split("-"))
    if not REFERENCE_WINDOW_MS[0] <= end - start <= REFERENCE_WINDOW_MS[1]:
        raise SystemExit(f"--window {text}: 11 to 30 s")
    return start, end


def reference_key(path, start_ms, end_ms):
    return f"{hashlib.sha256(path.read_bytes()).hexdigest()}:{start_ms}-{end_ms}"


def uploaded_references(directory):
    path = directory / UPLOADS
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def reference_excerpt(path, start_ms, end_ms):
    with tempfile.TemporaryDirectory() as work:
        excerpt = Path(work) / "reference.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start_ms / 1000), "-t", str((end_ms - start_ms) / 1000),
                        "-i", path, "-c:a", "libmp3lame", "-b:a", "192k", excerpt], check=True)
        return excerpt.read_bytes()


def upload_reference(path, window, directory, key):
    """Billed like a generation of the window's length; the song_id is kept in <out-dir>/references.json."""
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="reference.mp3"\r\n'
            f"Content-Type: audio/mpeg\r\n\r\n").encode("ascii") \
        + reference_excerpt(path, *window) + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(f"{API_URL}/upload", method="POST", data=body,
                                     headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            song_id = json.loads(response.read())["song_id"]
    except urllib.error.HTTPError as error:
        raise SystemExit(f"elevenlabs.io {error.code} on upload\n{error.read().decode('utf-8', 'replace')[:800]}") from None
    uploads = uploaded_references(directory)
    uploads[reference_key(path, *window)] = song_id
    (directory / UPLOADS).write_text(json.dumps(uploads, indent=1), encoding="utf-8")
    return song_id


def free_path(directory, name):
    path, number = directory / f"{name}.mp3", 1
    while path.exists():
        number += 1
        path = directory / f"{name}_{number}.mp3"
    return path


def generate(body, directory, name, key, lock):
    request = urllib.request.Request(f"{API_URL}?output_format={OUTPUT_FORMAT}", method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            audio, song_id = response.read(), response.headers.get("song-id")
    except urllib.error.HTTPError as error:
        # threading drops a SystemExit raised in a worker.
        print(f"elevenlabs.io {error.code}\n{error.read().decode('utf-8', 'replace')[:800]}", file=sys.stderr)
        return
    with lock:
        path = free_path(directory, name)
        path.write_bytes(audio)
    path.with_suffix(".json").write_text(json.dumps(body, indent=1), encoding="utf-8")
    print(f"→ {path} · song-id {song_id}", flush=True)


def arguments():
    parser = argparse.ArgumentParser(description="Music on elevenlabs.io from a track file")
    parser.add_argument("--track", required=True, help="file cut into [name | seconds | direction] sections")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--name", default="music", help="mp3 name, never overwritten (music_2.mp3…)")
    parser.add_argument("--takes", type=int, default=1, help="independent generations, run in parallel (2 at most)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and the cost, send nothing")
    parser.add_argument("--reference", type=Path, help="recording whose melody and style condition every section")
    parser.add_argument("--window", default="0-30", help="seconds of the reference to upload, 11 to 30 s")
    parser.add_argument("--strength", default="medium", choices=("low", "medium", "high"))
    return parser.parse_args()


def main():
    args = arguments()
    track = read_track(args.track)
    check(track)
    window = window_ms(args.window) if args.reference else None
    song_id = uploaded_references(args.out_dir).get(reference_key(args.reference, *window)) if args.reference else None
    upload_ms = window[1] - window[0] if args.reference and not song_id else 0
    print(f"{args.name} · {len(track.sections)} sections · {track.duration_ms / 1000:g} s · {args.takes} take(s) · "
          f"{args.takes * credits(track.duration_ms) + credits(upload_ms)} credits"
          + (f" (reference upload {credits(upload_ms)})" if upload_ms else ""))
    if args.dry_run:
        print(json.dumps(composition_plan(track, conditioning(song_id or "<to upload>", window, args.strength) if args.reference else {}), indent=1))
        return
    key, lock = api_key("ELEVENLABS_API_KEY"), threading.Lock()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.reference and not song_id:
        song_id = upload_reference(args.reference, window, args.out_dir, key)
    body = composition_plan(track, conditioning(song_id, window, args.strength) if args.reference else {})
    threads = [threading.Thread(target=generate, args=(body, args.out_dir, args.name, key, lock)) for _ in range(args.takes)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()

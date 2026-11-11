"""ElevenLabs voice and sound effects for a clip, plus level tools.

    python3 sound.py voice --text "I got tired of juggling five terminals." --out <clip>/voice/v1.mp3 [--voice <id>] [--speed 1.0]
    python3 sound.py effect --text "soft mechanical keyboard keystroke" --seconds 0.6 --out <clip>/effects/key.mp3
    python3 sound.py even --in <clip>/music/music.mp3 --out <clip>/music/music-even.mp3
    python3 sound.py energy --in <clip>/music/music.mp3

`voice` also writes <out>.json: each word and its timing, for the captions.
`energy` prints the level (dB) every 0.25 s: find a track's drop and hits to cut on them.
"""

import argparse
import array
import base64
import json
import math
import os
import subprocess
import urllib.error
import urllib.request

from env import api_key

API_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"


def post(endpoint, body):
    request = urllib.request.Request(f"{API_URL}/{endpoint}", method="POST", data=json.dumps(body).encode("utf-8"),
                                     headers={"xi-api-key": api_key("ELEVENLABS_API_KEY"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"ElevenLabs {error.code}\n{error.read().decode('utf-8', 'replace')[:800]}") from None


def write(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as file:
        file.write(content)
    print(path)


def words_of(alignment):
    words, current = [], None
    for character, start, end in zip(alignment["characters"], alignment["character_start_times_seconds"],
                                     alignment["character_end_times_seconds"]):
        if character.isspace():
            current = None
            continue
        if current is None:
            current = {"word": "", "start": start, "end": end}
            words.append(current)
        current["word"] += character
        current["end"] = end
    return words


def voice(args):
    body = {"text": args.text, "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.35, "speed": args.speed}}
    spoken = json.loads(post(f"text-to-speech/{args.voice}/with-timestamps?output_format=mp3_44100_128", body))
    write(args.out, base64.b64decode(spoken["audio_base64"]))
    timing = json.dumps({"text": args.text, "words": words_of(spoken["alignment"])}, indent=1)
    write(os.path.splitext(args.out)[0] + ".json", timing.encode("utf-8"))


def effect(args):
    body = {"text": args.text, "duration_seconds": args.seconds, "prompt_influence": 0.6, "model_id": "eleven_text_to_sound_v2"}
    write(args.out, post("sound-generation?output_format=mp3_44100_128", body))


def even(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.source, "-af", "dynaudnorm=f=150:g=9:p=0.9:m=20",
                    "-b:a", "192k", args.out], check=True)
    print(args.out)


def energy(args):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", args.source, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    samples, window = array.array("h", pcm), 2000
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        rms = math.sqrt(sum(sample * sample for sample in chunk) / len(chunk))
        print(f"{start / 8000:5.2f} s  {20 * math.log10(max(rms, 1) / 32768):4.0f} dB")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    voice_command = commands.add_parser("voice")
    voice_command.add_argument("--voice", default=DEFAULT_VOICE)
    voice_command.add_argument("--speed", type=float, default=1.0)
    effect_command = commands.add_parser("effect")
    effect_command.add_argument("--seconds", type=float, required=True)
    for command in (voice_command, effect_command):
        command.add_argument("--text", required=True)
        command.add_argument("--out", required=True)
    even_command = commands.add_parser("even")
    even_command.add_argument("--out", required=True)
    energy_command = commands.add_parser("energy")
    for command in (even_command, energy_command):
        command.add_argument("--in", dest="source", required=True)
    args = parser.parse_args()
    {"voice": voice, "effect": effect, "even": even, "energy": energy}[args.command](args)


if __name__ == "__main__":
    main()

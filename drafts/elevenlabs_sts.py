#!/usr/bin/env python3
"""
ElevenLabs Speech-to-Speech for Chinese Audio Recordings

Setup:
1. Sign up at https://elevenlabs.io (free: 20k credits/month)
2. Developers → API Keys → create key
3. export ELEVENLABS_API_KEY=your_key_here
4. pip install elevenlabs
5. python3 elevenlabs_sts.py

Usage:
    python3 elevenlabs_sts.py                          # auto-detect Apple Music folder
    python3 elevenlabs_sts.py path/to/folder/or/file   # explicit path
    python3 elevenlabs_sts.py --list-voices            # show voices without converting
    python3 elevenlabs_sts.py -o ~/Desktop/converted   # custom output folder
"""

import os
import sys
import argparse
import plistlib
from pathlib import Path
from urllib.parse import urlparse, unquote


SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}


def check_api_key():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not set.\n")
        print("Setup instructions:")
        print("  1. Sign up at https://elevenlabs.io (free: 20k credits/month)")
        print("  2. Go to Developers → API Keys → create a new key")
        print("  3. export ELEVENLABS_API_KEY=your_key_here")
        print("  4. pip install elevenlabs")
        print("  5. python3 elevenlabs_sts.py")
        sys.exit(1)
    return api_key


def find_apple_music_folder():
    plist_path = Path("~/Library/Preferences/com.apple.Music.plist").expanduser()
    if plist_path.exists():
        try:
            with open(plist_path, "rb") as f:
                prefs = plistlib.load(f)
            media_url = prefs.get("media-folder-url")
            if media_url:
                parsed = urlparse(media_url)
                folder = Path(unquote(parsed.path)) / "Music"
                if folder.exists():
                    return folder
        except Exception:
            pass
    fallback = Path("~/Music/Music/Media.localized/Music").expanduser()
    if fallback.exists():
        return fallback
    return None


def collect_audio_files(path):
    p = Path(path).expanduser().resolve()
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [p]
        else:
            print(f"Error: '{p}' is not a supported audio file ({', '.join(SUPPORTED_EXTENSIONS)})")
            sys.exit(1)
    elif p.is_dir():
        files = sorted(
            f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        return files
    else:
        print(f"Error: '{p}' does not exist.")
        sys.exit(1)


def list_voices(client):
    try:
        response = client.voices.get_all()
        voices = response.voices
    except Exception as e:
        print(f"Error fetching voices: {e}")
        sys.exit(1)
    return voices


def display_voices(voices):
    print("\nAvailable voices:")
    for i, voice in enumerate(voices):
        labels = voice.labels or {}
        gender = labels.get("gender", "")
        accent = labels.get("accent", "")
        detail = ", ".join(x for x in [gender, accent] if x)
        detail_str = f"  ({detail})" if detail else ""
        print(f"  [{i}] {voice.name}{detail_str}")
    print()


def pick_voice(voices):
    display_voices(voices)
    while True:
        raw = input("Enter number or voice name: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(voices):
                return voices[idx]
            print(f"  Please enter a number between 0 and {len(voices) - 1}.")
        else:
            matches = [v for v in voices if v.name.lower() == raw.lower()]
            if matches:
                return matches[0]
            close = [v for v in voices if raw.lower() in v.name.lower()]
            if close:
                print(f"  No exact match. Did you mean: {', '.join(v.name for v in close)}?")
            else:
                print(f"  Voice '{raw}' not found. Try again.")


def convert_file(client, input_path, output_path, voice):
    audio_bytes = input_path.read_bytes()
    chunks = client.speech_to_speech.convert(
        voice_id=voice.voice_id,
        model_id="eleven_multilingual_sts_v2",
        audio=audio_bytes,
        output_format="mp3_44100_128",
        remove_background_noise=True,
    )
    with open(output_path, "wb") as out:
        for chunk in chunks:
            out.write(chunk)


def main():
    parser = argparse.ArgumentParser(
        description="ElevenLabs Speech-to-Speech for Chinese audio recordings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Audio file or folder (default: auto-detect Apple Music folder)",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="DIR",
        help="Output folder (default: same folder as input file)",
    )
    args = parser.parse_args()

    api_key = check_api_key()

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        print("Error: elevenlabs package not installed.")
        print("Run: pip install elevenlabs")
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)

    if args.list_voices:
        voices = list_voices(client)
        display_voices(voices)
        return

    # Resolve input path
    if args.input:
        input_path = args.input
    else:
        folder = find_apple_music_folder()
        if not folder:
            print("Error: Could not auto-detect Apple Music folder.")
            print("Please provide a path: python3 elevenlabs_sts.py path/to/folder")
            sys.exit(1)
        print(f"Auto-detected Apple Music folder: {folder}")
        input_path = folder

    audio_files = collect_audio_files(input_path)

    if not audio_files:
        print("No supported audio files found.")
        sys.exit(0)

    print(f"\nFound {len(audio_files)} file(s):")
    for f in audio_files:
        print(f"  {f}")

    answer = input(f"\nFound {len(audio_files)} file(s). Continue? [y/n]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # Set up output folder
    output_dir = None
    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    voices = list_voices(client)

    while True:
        voice = pick_voice(voices)
        print(f"\nSelected voice: {voice.name} (ID: {voice.voice_id})")

        # Convert files
        total = len(audio_files)
        errors = 0
        output_paths = []
        for i, input_file in enumerate(audio_files, 1):
            stem = input_file.stem
            voice_slug = voice.name.split()[0]
            out_name = f"{stem}_{voice_slug}.mp3"
            out_path = (output_dir / out_name) if output_dir else (input_file.parent / out_name)
            output_paths.append(out_path)

            print(f"[{i}/{total}] Converting: {input_file.name} → {out_name} ...", end=" ", flush=True)
            try:
                convert_file(client, input_file, out_path, voice)
                print("✓")
            except Exception as e:
                print(f"✗\n  Error: {e}")
                errors += 1

        print(f"\nDone. {total - errors}/{total} file(s) converted successfully.")
        if errors:
            print(f"{errors} file(s) failed — check errors above.")

        # Open output files
        for p in output_paths:
            if p.exists():
                import subprocess
                subprocess.Popen(["open", str(p)])

        again = input("\nTry another voice? [y/n]: ").strip().lower()
        if again not in ("y", "yes"):
            break
        print()


if __name__ == "__main__":
    main()

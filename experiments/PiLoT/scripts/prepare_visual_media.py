#!/usr/bin/env python3
"""Prepare selected PNGs and browser-friendly video copies, without changing outputs/.

Requires ffmpeg with libx264 and ffprobe. Existing destination directories are
never overwritten. Run from an independent PiLoT source checkout after inference.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MAX_MEDIA_BYTES = 25 * 1024 * 1024
FRAMES = ("0_0.png", "1_0.png", "2_0.png")
CASES = {
    "feicuiwan_512": (("outputs/3dgs_test",), (512, 288), 299),
    "feicuiwan_1024": (("outputs/3dgs_test_1024",), (1024, 576), 299),
    "smbu_seq2": (("outputs/smbu_seq2_viz", "outputs/smbu_seq2"), (512, 288), 693),
}


def video_info(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames",
        "-of", "json", str(path),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    streams = json.loads(result.stdout).get("streams", [])
    if len(streams) != 1:
        raise ValueError("Expected one video stream: " + str(path))
    stream = streams[0]
    return {
        "codec": stream["codec_name"],
        "size": (int(stream["width"]), int(stream["height"])),
        "fps": Fraction(stream["avg_frame_rate"]),
        "frames": int(stream["nb_read_frames"]),
    }


def png_size(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Invalid PNG: " + str(path))
    return (int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big"))


def source_for(name):
    candidates, expected_size, expected_frames = CASES[name]
    for relative in candidates:
        directory = ROOT / relative
        files = [directory / filename for filename in FRAMES + ("visualization.mp4",)]
        if not all(path.is_file() and not path.is_symlink() for path in files):
            continue
        for path in files:
            path.resolve().relative_to(ROOT)
        for filename in FRAMES:
            image = directory / filename
            if png_size(image) != expected_size or image.stat().st_size > MAX_MEDIA_BYTES:
                raise ValueError("Unexpected image dimensions or size: " + str(image))
        info = video_info(directory / "visualization.mp4")
        if (info["size"] != expected_size or info["fps"] != 10
                or info["frames"] != expected_frames):
            raise ValueError("Unexpected resolution, frame rate or frame count: " + relative)
        return directory, info
    raise ValueError("Missing selected images/video for " + name + ": " + ", ".join(candidates))


def prepare(name, source, original_info, output_root):
    target = output_root / name
    # Create a complete group in a temporary directory before publishing it.
    with tempfile.TemporaryDirectory(prefix=".preparing-" + name + "-", dir=str(output_root)) as scratch:
        staging = Path(scratch) / name
        staging.mkdir()
        for filename in FRAMES:
            shutil.copy2(str(source / filename), str(staging / filename))
        video = staging / "visualization.mp4"
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(source / "visualization.mp4"), "-map", "0:v:0", "-an",
            "-map_metadata", "-1", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2",
            "-movflags", "+faststart", str(video),
        ], check=True)
        info = video_info(video)
        if (info["codec"] != "h264" or any(
                info[field] != original_info[field] for field in ("size", "fps", "frames"))):
            raise ValueError("Transcoded video does not match the original timing/dimensions")
        if video.stat().st_size > MAX_MEDIA_BYTES:
            raise ValueError("Prepared video exceeds the 25 MiB publishing limit")
        if target.exists() or target.is_symlink():
            raise ValueError("Refusing to overwrite existing media: " + str(target))
        staging.rename(target)
    print("PREPARED: {} ({} bytes video)".format(target, (target / "visualization.mp4").stat().st_size), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=tuple(CASES), default=list(CASES))
    parser.add_argument("--output-root", type=Path, default=ROOT / "docs/media")
    parser.add_argument("--check", action="store_true", help="Validate inputs and print the plan without writing files")
    args = parser.parse_args()
    if not (ROOT / "main.py").is_file() or not (ROOT / "pixloc").is_dir():
        parser.error("Run this helper in a complete PiLoT source checkout, not the lightweight collection")
    for command in ("ffmpeg", "ffprobe"):
        if shutil.which(command) is None:
            parser.error("Missing command: " + command + ". Install FFmpeg first.")
    encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if "libx264" not in encoders.stdout:
        parser.error("FFmpeg must provide the libx264 encoder")
    output_root = args.output_root.expanduser().absolute()
    if output_root.is_symlink():
        parser.error("The output root must not be a symbolic link")
    plan = [(name,) + source_for(name) for name in dict.fromkeys(args.cases)]
    for name, source, info in plan:
        target = output_root / name
        print("{}: {} -> {} | {}x{}, {} FPS, {} frames".format(
            name, source, target, *info["size"], info["fps"], info["frames"]), flush=True)
        if target.exists() or target.is_symlink():
            if not args.check:
                parser.error("Destination exists; refusing to overwrite: " + str(target))
            print("  NOTE: destination exists; actual preparation would refuse to overwrite.")
    if args.check:
        print("CHECK OK: no files written.")
        return
    output_root.mkdir(parents=True, exist_ok=True)
    for name, source, info in plan:
        prepare(name, source, info, output_root)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit("Media preparation failed: " + str(error))

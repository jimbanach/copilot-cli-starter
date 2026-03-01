#!/usr/bin/env python3
"""
extract_video_frames.py — Intelligent keyframe extraction for meeting videos.

Uses ffmpeg CLI for frame extraction and numpy+Pillow for scene-change detection.
Extracts only frames where visual content changes significantly (slides, screen
shares, demos, diagrams). Naturally filters out talking-head footage.

Works on ARM64 and x64 Windows. Requires: ffmpeg (system), numpy, Pillow.

Usage:
    python extract_video_frames.py extract <video_path> [--output-dir DIR] [--threshold 30] [--min-interval 2] [--max-frames 200]
    python extract_video_frames.py cleanup <directory>

Output:
    - Timestamped PNG keyframes in output directory
    - manifest.json with frame metadata (timestamp, filename, scene_score)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def check_dependencies():
    """Verify required packages and tools are installed."""
    missing_py = []
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing_py.append("numpy")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing_py.append("Pillow")
    if missing_py:
        print(f"ERROR: Missing Python packages: {', '.join(missing_py)}")
        print(f"Install with: pip install {' '.join(missing_py)}")
        sys.exit(1)

    for tool in ["ffmpeg", "ffprobe"]:
        try:
            subprocess.run([tool, "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"ERROR: {tool} not found. Install ffmpeg and ensure it's on PATH.")
            sys.exit(1)


def _get_video_info(video_path: str) -> dict:
    """Get video metadata via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", video_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {"fps": 30.0, "duration_sec": 0.0, "width": 0, "height": 0}

    data = json.loads(result.stdout)
    info = {"fps": 30.0, "duration_sec": 0.0, "width": 0, "height": 0}

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            fps_str = stream.get("r_frame_rate", "30/1")
            parts = fps_str.split("/")
            info["fps"] = float(parts[0]) / float(parts[1]) if len(parts) == 2 and float(parts[1]) > 0 else 30.0
            info["width"] = int(stream.get("width", 0))
            info["height"] = int(stream.get("height", 0))
            break

    fmt = data.get("format", {})
    info["duration_sec"] = float(fmt.get("duration", 0))
    return info


def _extract_raw_frames(video_path: str, output_dir: str, interval_sec: float = 1.0) -> list:
    """
    Extract frames at regular intervals using ffmpeg.
    Returns list of (timestamp_sec, filepath) tuples.
    """
    pattern = os.path.join(output_dir, "_raw_%06d.png")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval_sec}",
        "-q:v", "2",
        pattern,
        "-y", "-loglevel", "warning"
    ]
    subprocess.run(cmd, capture_output=True, text=True)

    frames = []
    idx = 1
    while True:
        fpath = os.path.join(output_dir, f"_raw_{idx:06d}.png")
        if not os.path.isfile(fpath):
            break
        timestamp = (idx - 1) * interval_sec
        frames.append((timestamp, fpath))
        idx += 1

    return frames


def extract_keyframes(
    video_path: str,
    output_dir: str,
    threshold: float = 30.0,
    min_interval: float = 2.0,
    max_frames: int = 200,
) -> dict:
    """
    Extract keyframes from a video using scene-change detection.

    Pipeline: ffmpeg extracts frames at 1/sec -> numpy compares consecutive
    frames -> only frames with significant visual changes are kept.

    Args:
        video_path: Path to the video file (.mp4, .mkv, etc.)
        output_dir: Directory to save extracted frames and manifest
        threshold: Scene change sensitivity (0-255 scale, mean pixel diff).
                   30 is good for slides/screen shares. Use 15 for subtle changes.
        min_interval: Minimum seconds between extracted keyframes
        max_frames: Maximum number of keyframes to keep (safety cap)

    Returns:
        dict with extraction results (frame_count, duration, manifest_path, etc.)
    """
    import numpy as np
    from PIL import Image

    video_path = str(Path(video_path).resolve())
    output_dir = str(Path(output_dir).resolve())

    if not os.path.isfile(video_path):
        return {"error": f"Video file not found: {video_path}"}

    os.makedirs(output_dir, exist_ok=True)
    raw_dir = os.path.join(output_dir, "_raw")
    os.makedirs(raw_dir, exist_ok=True)

    info = _get_video_info(video_path)
    duration_sec = info["duration_sec"]

    print(f"Video: {os.path.basename(video_path)}")
    print(f"Duration: {duration_sec / 60:.1f} min | FPS: {info['fps']:.1f} | Resolution: {info['width']}x{info['height']}")
    print(f"Settings: threshold={threshold}, min_interval={min_interval}s, max_frames={max_frames}")

    # Step 1: Extract raw frames at 1-second intervals using ffmpeg
    print("  Extracting raw frames (1 per second)...")
    raw_frames = _extract_raw_frames(video_path, raw_dir, interval_sec=1.0)
    print(f"  Got {len(raw_frames)} raw frames")

    if not raw_frames:
        shutil.rmtree(raw_dir, ignore_errors=True)
        return {"error": "No frames could be extracted from the video"}

    # Step 2: Scene-change detection
    print("  Running scene-change detection...")
    keyframes = []
    prev_gray = None
    prev_hist = None
    last_keep_time = -min_interval

    for timestamp, fpath in raw_frames:
        img = Image.open(fpath).convert("RGB")
        arr = np.array(img)

        gray = np.mean(arr, axis=2).astype(np.uint8)

        hist = np.concatenate([
            np.histogram(arr[:, :, c], bins=32, range=(0, 256))[0]
            for c in range(3)
        ]).astype(np.float64)
        norm = np.linalg.norm(hist)
        if norm > 0:
            hist = hist / norm

        if prev_gray is None:
            keyframes.append({
                "timestamp_sec": timestamp,
                "raw_path": fpath,
                "scene_score": 1.0,
                "reason": "first_frame",
            })
            prev_gray = gray
            prev_hist = hist
            last_keep_time = timestamp
            print(f"  [{_format_time(timestamp)}] First frame captured")
            continue

        if timestamp - last_keep_time < min_interval:
            prev_gray = gray
            prev_hist = hist
            continue

        # Compute scene change score
        pixel_diff = np.mean(np.abs(gray.astype(np.float64) - prev_gray.astype(np.float64)))
        hist_corr = np.dot(prev_hist, hist) if prev_hist is not None else 0.0
        hist_diff = (1.0 - hist_corr) * 128
        scene_score = hist_diff * 0.6 + pixel_diff * 0.4

        if scene_score >= threshold:
            keyframes.append({
                "timestamp_sec": round(timestamp, 2),
                "raw_path": fpath,
                "scene_score": round(float(scene_score), 2),
                "reason": "scene_change",
            })
            last_keep_time = timestamp
            print(f"  [{_format_time(timestamp)}] Scene change (score: {scene_score:.1f})")

            if len(keyframes) >= max_frames:
                print(f"  Reached max_frames cap ({max_frames})")
                break

        prev_gray = gray
        prev_hist = hist

    # Step 3: Copy keyframes to final location, remove raw frames
    print(f"  Saving {len(keyframes)} keyframes...")
    frames_manifest = []
    for i, kf in enumerate(keyframes):
        ts = kf["timestamp_sec"]
        fname = f"frame_{i:04d}_{_format_time(ts)}.png"
        dest = os.path.join(output_dir, fname)
        shutil.copy2(kf["raw_path"], dest)
        frames_manifest.append({
            "index": i,
            "timestamp_sec": kf["timestamp_sec"],
            "timestamp_fmt": _format_time(ts),
            "filename": fname,
            "scene_score": kf["scene_score"],
            "reason": kf["reason"],
        })

    shutil.rmtree(raw_dir, ignore_errors=True)

    # Write manifest
    manifest = {
        "video_file": os.path.basename(video_path),
        "video_path": video_path,
        "duration_sec": round(duration_sec, 2),
        "duration_fmt": _format_time(duration_sec),
        "fps": round(info["fps"], 2),
        "resolution": f"{info['width']}x{info['height']}",
        "extraction_settings": {
            "threshold": threshold,
            "min_interval_sec": min_interval,
            "max_frames": max_frames,
        },
        "frames_extracted": len(frames_manifest),
        "frames": frames_manifest,
        "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {len(frames_manifest)} keyframes extracted to {output_dir}")
    print(f"Manifest: {manifest_path}")

    return {
        "frame_count": len(frames_manifest),
        "duration_sec": round(duration_sec, 2),
        "output_dir": output_dir,
        "manifest_path": manifest_path,
    }


def _format_time(seconds: float) -> str:
    """Format seconds as HH-MM-SS for filenames."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}-{m:02d}-{s:02d}"


def cleanup(directory: str) -> dict:
    """Remove a temp directory and all its contents."""
    directory = str(Path(directory).resolve())
    if not os.path.isdir(directory):
        return {"error": f"Directory not found: {directory}", "cleaned": False}

    file_count = sum(1 for _ in Path(directory).rglob("*") if _.is_file())
    shutil.rmtree(directory)
    print(f"Cleaned up: {directory} ({file_count} files removed)")
    return {"cleaned": True, "directory": directory, "files_removed": file_count}


def main():
    parser = argparse.ArgumentParser(
        description="Extract keyframes from meeting videos using scene-change detection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract keyframes from a video")
    extract_parser.add_argument("video_path", help="Path to the video file")
    extract_parser.add_argument("--output-dir", default=None,
        help="Output directory for frames (default: temp dir next to video)")
    extract_parser.add_argument("--threshold", type=float, default=30.0,
        help="Scene change threshold 0-255 scale (default: 30, lower=more sensitive)")
    extract_parser.add_argument("--min-interval", type=float, default=2.0,
        help="Min seconds between frames (default: 2.0)")
    extract_parser.add_argument("--max-frames", type=int, default=200,
        help="Max frames to extract (default: 200)")

    cleanup_parser = subparsers.add_parser("cleanup", help="Remove temp frame directory")
    cleanup_parser.add_argument("directory", help="Directory to remove")

    args = parser.parse_args()

    if args.command == "extract":
        check_dependencies()
        output_dir = args.output_dir
        if output_dir is None:
            video_stem = Path(args.video_path).stem
            output_dir = os.path.join(
                os.path.dirname(args.video_path) or ".",
                f"_frames_{video_stem}"
            )
        result = extract_keyframes(
            video_path=args.video_path,
            output_dir=output_dir,
            threshold=args.threshold,
            min_interval=args.min_interval,
            max_frames=args.max_frames,
        )
        if "error" in result:
            print(f"ERROR: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "cleanup":
        result = cleanup(args.directory)
        if not result.get("cleaned"):
            print(f"ERROR: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

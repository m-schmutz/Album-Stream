from __future__ import annotations

import subprocess
from pathlib import Path


def generate_thumbnail(video_path: Path, thumb_path: Path) -> None:
    """
    Generate a thumbnail for the given video using ffmpeg.
    Grabs a frame at 1 second into the video.
    """
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        str(video_path),
        "-vframes",
        "1",
        "-q:v",
        "2",
        str(thumb_path),
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # In a real app, you'd log this
        pass

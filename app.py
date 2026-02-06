#!./env/bin/python3

from __future__ import annotations

import time
import uuid
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import (
    Flask,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from fileupdate import generate_thumbnail

import configparser

# Load config
config = configparser.ConfigParser()
config.read("config.ini")

HOST = config.get("server", "host", fallback="127.0.0.1")
PORT = config.getint("server", "port", fallback=5000)
DEBUG = config.getboolean("server", "debug", fallback=False)


app = Flask(__name__)

BASE_ALBUM_DIR: Path = Path("albums")
BASE_THUMB_DIR: Path = Path("thumbnails")

VIDEO_EXT: set[str] = {".mp4", ".mov", ".mkv", ".avi"}
COVER_NAME: str = "cover.jpg"

# token -> (album, video, expires_at)
SECRET_TOKENS: Dict[str, Tuple[str, str, float]] = {}

WIN_PROBABILITY: float = 0.25  # 25% chance

LAST_GLOBAL_SPIN_DATE = None


def ensure_dirs() -> None:
    BASE_ALBUM_DIR.mkdir(exist_ok=True)
    BASE_THUMB_DIR.mkdir(exist_ok=True)


def get_albums() -> List[str]:
    if not BASE_ALBUM_DIR.exists():
        return []
    return [p.name for p in BASE_ALBUM_DIR.iterdir() if p.is_dir()]


def get_album_cover(album: str) -> Optional[str]:
    cover_path = BASE_ALBUM_DIR / album / COVER_NAME
    if cover_path.exists():
        return url_for("album_cover", album=album)
    return None


def get_videos(album: str) -> List[str]:
    album_path = BASE_ALBUM_DIR / album
    if not album_path.exists():
        return []
    return [
        f.name
        for f in album_path.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXT
    ]


def get_secret_video_path(album: str, video: str) -> Path:
    """
    Secret videos stored as:
    albums/<album>/secret/<video_stem>_secret<ext>
    """
    src = Path(video)
    secret_dir = BASE_ALBUM_DIR / album / "secret"
    return secret_dir / f"{src.stem}_secret{src.suffix}"


@app.route("/")
def index() -> str:
    ensure_dirs()
    albums = get_albums()
    album_data = [
        {"name": album, "cover": get_album_cover(album)}
        for album in albums
    ]
    return render_template("index.html", albums=album_data)


@app.route("/album/<album>")
def album_page(album: str) -> str:
    videos = get_videos(album)
    if not videos:
        abort(404)
    return render_template("album.html", album=album, videos=videos)


@app.route("/video/<album>/<filename>")
def stream_video(album: str, filename: str):
    video_path = BASE_ALBUM_DIR / album / filename
    if not video_path.exists():
        abort(404)
    return send_file(video_path, mimetype="video/mp4")


@app.route("/thumbnail/<album>/<filename>")
def thumbnail(album: str, filename: str):
    thumb_path = BASE_THUMB_DIR / album / f"{filename}.jpg"
    if not thumb_path.exists():
        abort(404)
    return send_file(thumb_path, mimetype="image/jpeg")


@app.route("/album_cover/<album>")
def album_cover(album: str):
    cover_path = BASE_ALBUM_DIR / album / COVER_NAME
    if not cover_path.exists():
        abort(404)
    return send_file(cover_path, mimetype="image/jpeg")


@app.route("/upload", methods=["GET", "POST"])
def upload() -> str:
    ensure_dirs()

    if request.method == "GET":
        albums = get_albums()
        return render_template("upload.html", albums=albums)

    mode = request.form.get("mode")  # "existing" or "new"

    video_normal = request.files.get("video_normal")
    video_secret = request.files.get("video_secret")

    if not video_normal or not video_secret:
        abort(400, "Both normal and secret video files are required")

    if mode == "existing":
        album = request.form.get("existing_album")
        if not album:
            abort(400, "Existing album not selected")
        album_path = BASE_ALBUM_DIR / album
        if not album_path.exists():
            abort(400, "Album does not exist")
        cover_required = False
        cover_file = None
    elif mode == "new":
        album = request.form.get("new_album_name", "").strip()
        if not album:
            abort(400, "New album name is required")
        album = secure_filename(album)
        album_path = BASE_ALBUM_DIR / album
        album_path.mkdir(parents=True, exist_ok=True)

        cover_file = request.files.get("cover")
        if not cover_file:
            abort(400, "Cover image is required for new album")
        cover_required = True
    else:
        abort(400, "Invalid upload mode")

    # Save normal video
    normal_filename = secure_filename(video_normal.filename)
    if not normal_filename:
        abort(400, "Invalid normal video filename")

    normal_path = album_path / normal_filename
    video_normal.save(normal_path)

    # Save secret video
    secret_filename = secure_filename(video_secret.filename)
    if not secret_filename:
        abort(400, "Invalid secret video filename")

    secret_dir = album_path / "secret"
    secret_dir.mkdir(parents=True, exist_ok=True)

    secret_src = Path(normal_filename)
    secret_path = secret_dir / f"{secret_src.stem}_secret{secret_src.suffix}"
    video_secret.save(secret_path)

    # Save cover if new album
    if cover_required and cover_file:
        cover_path = album_path / COVER_NAME
        cover_file.save(cover_path)

    # Generate thumbnail for normal video
    thumb_album_dir = BASE_THUMB_DIR / album
    thumb_album_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_album_dir / f"{normal_filename}.jpg"
    generate_thumbnail(normal_path, thumb_path)

    return redirect(url_for("album_page", album=album))


@app.route("/wheel/<album>/<video>")
def wheel(album: str, video: str):
    # Ensure album/video exist
    video_path = BASE_ALBUM_DIR / album / video
    if not video_path.exists():
        abort(404)
    return render_template("wheel.html", album=album, video=video)


@app.route("/spin/<album>/<video>", methods=["POST"])
def spin(album: str, video: str):
    global LAST_GLOBAL_SPIN_DATE

    today_str = time.strftime("%Y-%m-%d")

    # GLOBAL check — applies to all devices, all browsers
    if LAST_GLOBAL_SPIN_DATE == today_str:
        return {"allowed": False, "reason": "already_spun"}

    # Perform spin
    win = random.random() < WIN_PROBABILITY

    # Update global spin date
    LAST_GLOBAL_SPIN_DATE = today_str

    resp_data = {"allowed": True, "win": win}

    if win:
        token = uuid.uuid4().hex
        expires_at = time.time() + 600
        SECRET_TOKENS[token] = (album, video, expires_at)
        resp_data["secret_url"] = url_for("secret_video", token=token)

    return resp_data



@app.route("/secret/<token>")
def secret_video(token: str):
    entry = SECRET_TOKENS.get(token)
    if not entry:
        abort(404)

    album, video, expires_at = entry
    if time.time() > expires_at:
        SECRET_TOKENS.pop(token, None)
        abort(410)  # Gone

    # Ensure secret file exists
    secret_path = get_secret_video_path(album, video)
    if not secret_path.exists():
        abort(404)

    return render_template(
        "secret_video.html",
        album=album,
        video=video,
        token=token,
    )


@app.route("/secret_stream/<token>")
def secret_stream(token: str):
    entry = SECRET_TOKENS.get(token)
    if not entry:
        abort(404)

    album, video, expires_at = entry
    if time.time() > expires_at:
        SECRET_TOKENS.pop(token, None)
        abort(410)

    secret_path = get_secret_video_path(album, video)
    if not secret_path.exists():
        abort(404)

    return send_file(secret_path, mimetype="video/mp4")


if __name__ == "__main__":
    ensure_dirs()
    app.run(host=HOST, port=PORT, debug=DEBUG)

from flask import Blueprint, render_template, current_app, abort, send_file
import json
import os
import time

from blueprints.spin import load_spin_state

albums_bp = Blueprint("albums", __name__, url_prefix="/albums")


def load_albums():
    path = current_app.config["ALBUMS_JSON"]
    if not os.path.exists(path):
        return {"albums": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"albums": []}


@albums_bp.route("/<album_id>")
def view_album(album_id):
    data = load_albums()
    albums = data.get("albums", [])
    album = next((a for a in albums if a["id"] == album_id), None)
    if album is None:
        abort(404)

    spin_state = load_spin_state()
    last_spin = spin_state.get(album_id)
    remaining_seconds = 0
    if last_spin is not None:
        elapsed = time.time() - last_spin
        cooldown = current_app.config["SPIN_COOLDOWN_SECONDS"]
        if elapsed < cooldown:
            remaining_seconds = int(cooldown - elapsed)

    return render_template(
        "album.html",
        album=album,
        remaining_seconds=remaining_seconds,
    )


@albums_bp.route("/<album_id>/video/<video_id>/<version>")
def play_video(album_id, video_id, version):
    if version not in ("main", "uncensored", "pixelated"):
        abort(404)

    data = load_albums()
    albums = data.get("albums", [])
    album = next((a for a in albums if a["id"] == album_id), None)
    if album is None:
        abort(404)

    video = next((v for v in album.get("videos", []) if v["id"] == video_id), None)
    if video is None:
        abort(404)

    key = f"{version}_path"
    video_path = video.get(key)
    if not video_path or not os.path.exists(video_path):
        abort(404)

    return send_file(video_path, mimetype="video/mp4")

from flask import Blueprint, send_file, abort, current_app
import os

media_bp = Blueprint("media", __name__, url_prefix="/media")


def safe_join(*parts):
    base = os.path.abspath(current_app.config["UPLOADS_DIR"])
    path = os.path.abspath(os.path.join(base, *parts))
    if not path.startswith(base):
        abort(403)
    return path


@media_bp.route("/<album_id>/cover")
def serve_cover(album_id):
    album_dir = safe_join(album_id, "cover")
    for ext in ("jpg", "jpeg", "png"):
        p = os.path.join(album_dir, f"cover.{ext}")
        if os.path.exists(p):
            return send_file(p)
    abort(404)


@media_bp.route("/<album_id>/thumb/<video_id>.jpg")
def serve_thumbnail(album_id, video_id):
    thumb_path = safe_join(album_id, "thumbnails", f"{video_id}.jpg")
    if not os.path.exists(thumb_path):
        abort(404)
    return send_file(thumb_path)

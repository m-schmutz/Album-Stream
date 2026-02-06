from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    current_app,
    flash,
)
import json
import os
import subprocess
from PIL import Image
import time

upload_bp = Blueprint("upload", __name__)

# ---------- helpers ----------


def load_albums():
    path = current_app.config["ALBUMS_JSON"]
    if not os.path.exists(path):
        return {"albums": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"albums": []}


def save_albums(data):
    path = current_app.config["ALBUMS_JSON"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def next_album_id(albums):
    existing_ids = [a["id"] for a in albums]
    max_num = 0
    for aid in existing_ids:
        if aid.startswith("album_"):
            try:
                num = int(aid.split("_")[1])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"album_{max_num + 1:03d}"


def next_video_id(album):
    existing_ids = [v["id"] for v in album.get("videos", [])]
    max_num = 0
    for vid in existing_ids:
        if vid.startswith("video_"):
            try:
                num = int(vid.split("_")[1])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"video_{max_num + 1:03d}"


def allowed_file(filename, allowed_exts):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_exts


def check_cover_aspect_ratio(path):
    img = Image.open(path)
    w, h = img.size
    ratio = w / h
    target = current_app.config["COVER_ASPECT_RATIO"]
    tol = current_app.config["COVER_ASPECT_TOLERANCE"]
    return abs(ratio - target) <= tol


def generate_thumbnail(video_path, thumbnail_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "1",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        thumbnail_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


# ---------- routes ----------


@upload_bp.route("/albums/new", methods=["GET", "POST"])
def create_album():
    if request.method == "GET":
        return render_template("create_album.html")

    album_name = request.form.get("name", "").strip()
    cover_file = request.files.get("cover")

    if not album_name:
        flash("Album name is required.", "error")
        return render_template("create_album.html")

    if not cover_file or cover_file.filename == "":
        flash("Cover image is required.", "error")
        return render_template("create_album.html")

    if not allowed_file(
        cover_file.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    ):
        flash("Invalid cover image format.", "error")
        return render_template("create_album.html")

    data = load_albums()
    albums = data.get("albums", [])

    album_id = next_album_id(albums)
    album_dir = os.path.join(current_app.config["UPLOADS_DIR"], album_id)
    cover_dir = os.path.join(album_dir, "cover")
    videos_dir = os.path.join(album_dir, "videos")
    thumbs_dir = os.path.join(album_dir, "thumbnails")

    os.makedirs(cover_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

    ext = cover_file.filename.rsplit(".", 1)[1].lower()
    cover_path = os.path.join(cover_dir, f"cover.{ext}")
    cover_file.save(cover_path)

    if not check_cover_aspect_ratio(cover_path):
        os.remove(cover_path)
        flash("Cover image must be 4:3 aspect ratio.", "error")
        return render_template("create_album.html")

    album = {
        "id": album_id,
        "name": album_name,
        "cover_path": cover_path,
        "created_at": time.time(),
        "videos": [],
    }
    albums.append(album)
    data["albums"] = albums
    save_albums(data)

    return redirect(url_for("albums.view_album", album_id=album_id))


@upload_bp.route("/albums/<album_id>/cover", methods=["POST"])
def change_cover(album_id):
    cover_file = request.files.get("cover")
    if not cover_file or cover_file.filename == "":
        flash("Cover image is required.", "error")
        return redirect(url_for("albums.view_album", album_id=album_id))

    if not allowed_file(
        cover_file.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    ):
        flash("Invalid cover image format.", "error")
        return redirect(url_for("albums.view_album", album_id=album_id))

    data = load_albums()
    albums = data.get("albums", [])
    album = next((a for a in albums if a["id"] == album_id), None)
    if album is None:
        flash("Album not found.", "error")
        return redirect(url_for("main.index"))

    album_dir = os.path.join(current_app.config["UPLOADS_DIR"], album_id)
    cover_dir = os.path.join(album_dir, "cover")
    os.makedirs(cover_dir, exist_ok=True)

    ext = cover_file.filename.rsplit(".", 1)[1].lower()
    cover_path = os.path.join(cover_dir, f"cover.{ext}")
    cover_file.save(cover_path)

    if not check_cover_aspect_ratio(cover_path):
        os.remove(cover_path)
        flash("Cover image must be 4:3 aspect ratio.", "error")
        return redirect(url_for("albums.view_album", album_id=album_id))

    album["cover_path"] = cover_path
    save_albums(data)

    return redirect(url_for("albums.view_album", album_id=album_id))


@upload_bp.route("/upload", methods=["GET", "POST"])
def upload_video():
    data = load_albums()
    albums = data.get("albums", [])

    if request.method == "GET":
        return render_template("upload_video.html", albums=albums)

    album_id = request.form.get("album_id")
    title = request.form.get("title", "").strip()

    main_file = request.files.get("main_video")
    uncensored_file = request.files.get("uncensored_video")
    pixelated_file = request.files.get("pixelated_video")

    if not album_id:
        flash("Album is required.", "error")
        return render_template("upload_video.html", albums=albums)

    album = next((a for a in albums if a["id"] == album_id), None)
    if album is None:
        flash("Album not found.", "error")
        return render_template("upload_video.html", albums=albums)

    if not main_file or main_file.filename == "":
        flash("Main video is required.", "error")
        return render_template("upload_video.html", albums=albums)

    if not uncensored_file or uncensored_file.filename == "":
        flash("Uncensored video is required.", "error")
        return render_template("upload_video.html", albums=albums)

    if not pixelated_file or pixelated_file.filename == "":
        flash("Pixelated video is required.", "error")
        return render_template("upload_video.html", albums=albums)

    for f in (main_file, uncensored_file, pixelated_file):
        if not allowed_file(
            f.filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
        ):
            flash("All videos must be mp4.", "error")
            return render_template("upload_video.html", albums=albums)

    album_dir = os.path.join(current_app.config["UPLOADS_DIR"], album_id)
    videos_dir = os.path.join(album_dir, "videos")
    thumbs_dir = os.path.join(album_dir, "thumbnails")
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

    video_id = next_video_id(album)

    main_path = os.path.join(videos_dir, f"{video_id}_main.mp4")
    uncensored_path = os.path.join(videos_dir, f"{video_id}_uncensored.mp4")
    pixelated_path = os.path.join(videos_dir, f"{video_id}_pixelated.mp4")
    thumb_path = os.path.join(thumbs_dir, f"{video_id}.jpg")

    main_file.save(main_path)
    uncensored_file.save(uncensored_path)
    pixelated_file.save(pixelated_path)

    generate_thumbnail(main_path, thumb_path)

    video_entry = {
        "id": video_id,
        "title": title or video_id,
        "main_path": main_path,
        "uncensored_path": uncensored_path,
        "pixelated_path": pixelated_path,
        "thumbnail_path": thumb_path,
        "uploaded_at": time.time(),
    }

    album.setdefault("videos", []).append(video_entry)
    save_albums(data)

    return redirect(url_for("albums.view_album", album_id=album_id))

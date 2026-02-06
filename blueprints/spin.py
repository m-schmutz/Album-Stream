from flask import (
    Blueprint,
    render_template,
    current_app,
    redirect,
    url_for,
    abort,
    request,
    make_response
)
import json
import os
import time
import random

spin_bp = Blueprint("spin", __name__, url_prefix="/spin")

_spin_state_cache = None


def load_spin_state():
    global _spin_state_cache
    if _spin_state_cache is not None:
        return _spin_state_cache

    path = current_app.config["SPIN_STATE_JSON"]
    if not os.path.exists(path):
        _spin_state_cache = {}
        return _spin_state_cache

    try:
        with open(path, "r", encoding="utf-8") as f:
            _spin_state_cache = json.load(f)
    except json.JSONDecodeError:
        _spin_state_cache = {}
    return _spin_state_cache


def save_spin_state():
    path = current_app.config["SPIN_STATE_JSON"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_spin_state_cache or {}, f, indent=2)


def can_spin(album_id):
    state = load_spin_state()
    last = state.get(album_id)
    if last is None:
        return True, 0

    elapsed = time.time() - last
    cooldown = current_app.config["SPIN_COOLDOWN_SECONDS"]

    if elapsed >= cooldown:
        return True, 0

    return False, int(cooldown - elapsed)

@spin_bp.route("/<album_id>/<video_id>", methods=["GET"])
def spin(album_id, video_id):
    allowed, remaining = can_spin(album_id)
    result = request.args.get("result")

    response = make_response(render_template(
        "spin.html",
        album_id=album_id,
        video_id=video_id,
        allowed=allowed,
        remaining_seconds=remaining,
        win_probability=current_app.config["SPIN_WIN_PROBABILITY"],
        result=result,
    ))

    # 🚫 Prevent browser caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response



@spin_bp.route("/<album_id>/<video_id>/start", methods=["POST"])
def start_spin(album_id, video_id):
    allowed, remaining = can_spin(album_id)

    if not allowed:
        return redirect(url_for("spin.spin", album_id=album_id, video_id=video_id))

    win_prob = current_app.config["SPIN_WIN_PROBABILITY"]
    win = random.random() < win_prob

    # DO NOT save timestamp yet — wait until after animation
    return render_template(
    "spin.html",
    album_id=album_id,
    video_id=video_id,
    allowed=True,
    remaining_seconds=0,
    win_probability=current_app.config["SPIN_WIN_PROBABILITY"],
    result="win" if win else "lose",
)



@spin_bp.route("/<album_id>/<video_id>/mark_spun", methods=["POST"])
def mark_spun(album_id, video_id):
    state = load_spin_state()
    state[album_id] = time.time()
    save_spin_state()
    return "", 204


@spin_bp.route("/<album_id>/<video_id>/force_win")
def force_win(album_id, video_id):
    if not current_app.config["DEBUG"]:
        abort(404)
    return redirect(
        url_for("albums.play_video", album_id=album_id, video_id=video_id, version="uncensored")
    )


@spin_bp.route("/<album_id>/<video_id>/force_lose")
def force_lose(album_id, video_id):
    if not current_app.config["DEBUG"]:
        abort(404)
    return redirect(
        url_for("albums.play_video", album_id=album_id, video_id=video_id, version="pixelated")
    )

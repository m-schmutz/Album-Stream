from flask import Blueprint, render_template, current_app
import json
import os

main_bp = Blueprint("main", __name__)


def load_albums():
    path = current_app.config["ALBUMS_JSON"]
    if not os.path.exists(path):
        return {"albums": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"albums": []}


@main_bp.route("/")
def index():
    data = load_albums()
    albums = data.get("albums", [])
    return render_template("main.html", albums=albums)

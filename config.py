import os

HOST = "127.0.0.1"
PORT = 5000
DEBUG = True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

ALBUMS_JSON = os.path.join(DATA_DIR, "albums.json")
SPIN_STATE_JSON = os.path.join(DATA_DIR, "spin_state.json")

SPIN_WIN_PROBABILITY = 0.10  # 10%
SPIN_COOLDOWN_SECONDS = 24 * 60 * 60  # 24 hours

ALLOWED_VIDEO_EXTENSIONS = {"mp4"}
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
COVER_ASPECT_RATIO = 4 / 3
COVER_ASPECT_TOLERANCE = 0.02  # small tolerance

from flask import Flask
import config
from blueprints.main import main_bp
from blueprints.albums import albums_bp
from blueprints.upload import upload_bp
from blueprints.spin import spin_bp
from blueprints.media import media_bp
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Ensure data and uploads directories exist
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)

    app.register_blueprint(main_bp)
    app.register_blueprint(albums_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(spin_bp)
    app.register_blueprint(media_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
    )

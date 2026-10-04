import os

from dotenv import load_dotenv
from flask import Flask, send_from_directory


def create_app():
    load_dotenv()   # reads GITHUB_TOKEN and GEMINI_API_KEY from the .env file
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="/static")

    from app.routes import bp
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    return app
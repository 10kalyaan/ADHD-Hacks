from flask import Flask
from flask_cors import CORS

from config import PORT
from vectordb.client import ensure_collections
from ingestion.routes import ingestion_bp
from nudging.routes import nudging_bp


def create_app():
    app = Flask(__name__)
    CORS(app)  # extension pages run on chrome-extension:// origins

    ensure_collections()

    app.register_blueprint(ingestion_bp)
    app.register_blueprint(nudging_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=PORT, debug=True)

"""Punto de entrada principal de la aplicación EduGest PME."""
import os
from app import create_app

app = create_app(config_name=os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", True))
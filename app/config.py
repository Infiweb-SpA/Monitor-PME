"""Configuración centralizada de la aplicación EduGest PME."""
import os
from datetime import timedelta


class Config:
    """Configuración base compartida por todos los entornos."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "edugest-dev-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///edugest_pme.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Parámetros del algoritmo PME
    UMBRAL_SEMAFORO_ROJO = 0.85
    UMBRAL_SEMAFORO_AMARILLO = 0.95
    UMBRAL_SEMAFORO_VERDE = 1.0

    # Configuración de carga de archivos
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False


class TestingConfig(Config):
    """Configuración para pruebas unitarias."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_por_entorno = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
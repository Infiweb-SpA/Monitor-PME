"""Paquete de modelos SQLAlchemy para EduGest PME."""
from app.extensions import db

# Importa todos los modelos para que SQLAlchemy los registre
from app.models.user import User
from app.models.pme import (
    Establecimiento,
    DimensionPME,
    ObjetivoPME,
    AccionPME,
    Curso,
)
from app.models.metrics import (
    Estudiante,
    RegistroAppPonderado,
    MetricaSIGE,
    ParticipacionAccion,
    IndicadorAccion,
)

__all__ = [
    "db",
    "User",
    "Establecimiento",
    "DimensionPME",
    "ObjetivoPME",
    "AccionPME",
    "Curso",
    "Estudiante",
    "RegistroAppPonderado",
    "MetricaSIGE",
    "ParticipacionAccion",
    "IndicadorAccion",
]
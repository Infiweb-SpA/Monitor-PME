"""Utilidades compartidas para EduGest PME."""
from datetime import datetime, date
import pandas as pd


def parse_date(fecha_str):
    """Convierte un string 'YYYY-MM-DD' a un objeto date de Python.

    Maneja múltiples formatos de entrada:
    - String 'YYYY-MM-DD' (formularios HTML)
    - pd.Timestamp (archivos Excel vía pandas)
    - date (ya es un objeto date)
    - None / NaN

    Returns:
        date o None si no se puede convertir.
    """
    if fecha_str is None:
        return None

    # Verificar NaN de pandas
    try:
        if pd.isna(fecha_str):
            return None
    except (TypeError, ValueError):
        pass

    try:
        # Si viene de Pandas (Timestamp)
        if isinstance(fecha_str, pd.Timestamp):
            return fecha_str.date()
        # Si ya es un date
        if isinstance(fecha_str, date):
            return fecha_str
        # Si viene de un formulario HTML (String)
        if isinstance(fecha_str, str):
            fecha_str = fecha_str.strip()
            if not fecha_str:
                return None
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None

    return None
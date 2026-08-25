"""Procesamiento de cargas manuales y archivos CSV/Excel."""
import pandas as pd
from io import BytesIO


def procesar_csv_acciones(file_stream):
    """Procesa un archivo CSV con registros de acciones PME (F-1)."""
    try:
        df = pd.read_csv(file_stream)
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}


def procesar_excel_metricas(file_stream):
    """Procesa un archivo Excel con métricas SIGE o App Ponderado."""
    try:
        df = pd.read_excel(BytesIO(file_stream.read()))
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}
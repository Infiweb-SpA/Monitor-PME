"""Motor algorítmico de cálculo cuantitativo PME.

Incluye:
- Índice de Eficiencia de Acción (IEA)
- Correlación de Pearson
- Algoritmo de Semáforo / Proyección de Cumplimiento
"""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia):
    """Calcula el Índice de Eficiencia de Acción (IEA).

    Fórmula conceptual: impacto generado / recurso invertido.
    Retorna valor entre 0.0 y 5.0.
    """
    if gasto_ejecutado <= 0 or horas_ejecutadas <= 0:
        return 0.0

    impacto = (delta_rendimiento * 0.6) + (delta_asistencia * 0.4)
    recurso = (gasto_ejecutado / 1_000_000) + (horas_ejecutadas / 10)
    iea = min(5.0, max(0.0, (impacto / recurso) * 10))
    return round(iea, 2)


def calcular_correlacion_pearson(x, y):
    """Calcula el coeficiente de correlación de Pearson entre dos arrays.

    Args:
        x: Array de valores (ej. horas de asistencia a taller).
        y: Array de valores (ej. mejora en notas).

    Returns:
        tuple: (coeficiente_r, valor_p)
    """
    if len(x) < 2 or len(y) < 2 or len(x) != len(y):
        return None, None
    try:
        r, p = pearsonr(x, y)
        return round(r, 3), round(p, 4)
    except Exception:
        return None, None


def determinar_semaforo(proyeccion_cumplimiento, umbral_rojo=0.85, umbral_amarillo=0.95):
    """Determina el estado del semáforo según proyección de cumplimiento.

    Args:
        proyeccion_cumplimiento: Valor entre 0.0 y 1.0+
        umbral_rojo: Límite inferior (default 0.85)
        umbral_amarillo: Límite medio (default 0.95)

    Returns:
        str: "Rojo", "Amarillo" o "Verde"
    """
    if proyeccion_cumplimiento < umbral_rojo:
        return "Rojo"
    elif proyeccion_cumplimiento < umbral_amarillo:
        return "Amarillo"
    return "Verde"


def proyectar_cumplimiento(valores_historicos, meta):
    """Proyecta el cumplimiento a fin de año usando regresión lineal simple.

    Args:
        valores_historicos: Lista de valores mensuales acumulados.
        meta: Valor objetivo a alcanzar.

    Returns:
        float: Proyección de cumplimiento (0.0 - 1.0+)
    """
    if not valores_historicos or meta <= 0:
        return 0.0

    n = len(valores_historicos)
    if n < 2:
        return min(1.0, valores_historicos[-1] / meta) if valores_historicos else 0.0

    x = np.arange(n)
    y = np.array(valores_historicos)

    # Regresión lineal: y = mx + b
    m, b = np.polyfit(x, y, 1)

    # Proyectar al mes 12 (índice 11, 0-based)
    proyeccion = m * 11 + b
    cumplimiento = proyeccion / meta

    return round(min(2.0, max(0.0, cumplimiento)), 3)
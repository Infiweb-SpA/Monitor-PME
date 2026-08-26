"""Motor algorítmico de cálculo cuantitativo PME.

Incluye:
- Índice de Eficiencia de Acción (IEA) con escalas normalizadas y penalización por sobregiro
- Correlación de Pearson (horas de taller vs mejora de notas)
- Algoritmo de Semáforo / Proyección de Cumplimiento
"""
import numpy as np
from app.extensions import db
from app.models.pme import AccionPME
from app.models.metrics import RegistroAppPonderado, ParticipacionAccion, IndicadorAccion, Estudiante


# ============================================================
# FUNCIONES MATEMÁTICAS PURAS
# ============================================================

def calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia,
                 presupuesto_asignado=None):
    """Calcula el Índice de Eficiencia de Acción (IEA).

    Escalas NORMALIZADAS para que sean comparables:
    - Notas (1.0-7.0): una mejora de +1.0 punto es el tope razonable.
    - Asistencia (0-100): una mejora de +10% es el tope razonable → se divide por 10.

    Penalización por sobregiro: si gasto > presupuesto, el IEA se reduce
    proporcionalmente (presupuesto / gasto).
    """
    if gasto_ejecutado <= 0 or horas_ejecutadas <= 0:
        return 0.0

    # Normalización de escalas (recorta extremos absurdos)
    delta_rend_norm = max(-2.0, min(2.0, delta_rendimiento))
    delta_asist_norm = max(-10.0, min(10.0, delta_asistencia)) / 10.0

    impacto = (delta_rend_norm * 0.6) + (delta_asist_norm * 0.4)
    recurso = (gasto_ejecutado / 1_000_000) + (horas_ejecutadas / 10)

    if recurso <= 0:
        return 0.0

    iea = (impacto / recurso) * 10

    # PENALIZACIÓN POR SOBREGIRO PRESUPUESTARIO
    if presupuesto_asignado and presupuesto_asignado > 0:
        if gasto_ejecutado > presupuesto_asignado:
            factor = presupuesto_asignado / gasto_ejecutado
            iea *= factor

    return round(min(5.0, max(0.0, iea)), 2)


def calcular_correlacion_pearson(x, y):
    """Coeficiente de Pearson entre dos arrays."""
    if len(x) < 2 or len(y) < 2 or len(x) != len(y):
        return None, None
    try:
        r = np.corrcoef(x, y)[0, 1]
        if np.isnan(r):
            return None, None
        return round(float(r), 3), 0.0
    except Exception:
        return None, None


def determinar_semaforo(proyeccion_cumplimiento, umbral_rojo=0.85, umbral_amarillo=0.95):
    if proyeccion_cumplimiento < umbral_rojo:
        return "Rojo"
    elif proyeccion_cumplimiento < umbral_amarillo:
        return "Amarillo"
    return "Verde"


def proyectar_cumplimiento(valores_historicos, meta, x_indices=None, mes_objetivo=11):
    """Proyección de cumplimiento a fin de año (noviembre = índice 11).

    Args:
        valores_historicos: Serie de valores (promedio del grupo por periodo).
        x_indices: (Opcional) Número de mes real de cada valor (ej: marzo=3).
                   Si no se entrega, se asumen periodos consecutivos.
    """
    if not valores_historicos or meta <= 0:
        return 0.0

    n = len(valores_historicos)
    if n < 2:
        return min(1.0, valores_historicos[-1] / meta) if valores_historicos else 0.0

    if x_indices is None:
        x = np.arange(n)
    else:
        x = np.array(x_indices[:n], dtype=float)

    y = np.array(valores_historicos, dtype=float)

    m, b = np.polyfit(x, y, 1)
    proyeccion = m * mes_objetivo + b
    cumplimiento = proyeccion / meta

    return round(min(2.0, max(0.0, cumplimiento)), 3)


# ============================================================
# HELPERS DE CONSULTA (robustos a duplicados)
# ============================================================

def _nota_promedio(estudiante_id, periodo):
    """Promedio de TODAS las notas del estudiante en un periodo (evita tomar un registro arbitrario)."""
    regs = RegistroAppPonderado.query.filter_by(
        estudiante_id=estudiante_id, periodo=periodo
    ).all()
    if not regs:
        return None
    return float(np.mean([r.promedio_notas for r in regs]))


def _asistencia_promedio(estudiante_id, periodo):
    regs = RegistroAppPonderado.query.filter_by(
        estudiante_id=estudiante_id, periodo=periodo
    ).all()
    if not regs:
        return None
    return float(np.mean([r.porcentaje_asistencia for r in regs]))


def _primer_periodo(estudiante_id):
    """El periodo más antiguo con datos del estudiante."""
    reg = RegistroAppPonderado.query.filter_by(estudiante_id=estudiante_id)\
        .order_by(RegistroAppPonderado.periodo.asc()).first()
    return reg.periodo if reg else None


# ============================================================
# ORQUESTADOR PRINCIPAL
# ============================================================

def procesar_indicadores_accion(accion_id, periodo):
    """Une la base de datos con el motor algorítmico y guarda IndicadorAccion."""
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return None

    participaciones = ParticipacionAccion.query.filter_by(accion_id=accion_id).all()
    if not participaciones:
        return None

    # Horas acumuladas por estudiante (si participó varias veces, se suman)
    horas_por_est = {}
    for p in participaciones:
        horas_por_est[p.estudiante_id] = horas_por_est.get(p.estudiante_id, 0) + p.horas_asistencia

    estudiante_ids = list(horas_por_est.keys())
    horas_totales = sum(horas_por_est.values())
    gasto_total = accion.presupuesto_ejecutado

    x_horas, y_deltas = [], []
    notas_actuales, asist_actuales, asist_iniciales = [], [], []

    for est_id in estudiante_ids:
        nota_actual = _nota_promedio(est_id, periodo)
        if nota_actual is None:
            continue  # Sin notas en el periodo → no aporta al cálculo

        periodo_inicial = _primer_periodo(est_id)
        nota_inicial = _nota_promedio(est_id, periodo_inicial) if periodo_inicial else None
        if nota_inicial is None:
            nota_inicial = accion.linea_base_valor or 0.0

        x_horas.append(horas_por_est[est_id])
        y_deltas.append(nota_actual - nota_inicial)
        notas_actuales.append(nota_actual)

        asist_act = _asistencia_promedio(est_id, periodo)
        asist_ini = _asistencia_promedio(est_id, periodo_inicial) if periodo_inicial else None
        if asist_act is not None:
            asist_actuales.append(asist_act)
        if asist_ini is not None:
            asist_iniciales.append(asist_ini)

    if not notas_actuales:
        return None

    # --- Deltas del GRUPO (normalizados en calcular_iea) ---
    if accion.indicador_tipo == "Asistencia":
        delta_rendimiento = 0.0
        base_asist = np.mean(asist_iniciales) if asist_iniciales else (accion.linea_base_valor or 0)
        delta_asistencia = np.mean(asist_actuales) - base_asist
    else:
        delta_rendimiento = np.mean(notas_actuales) - (accion.linea_base_valor or 0)
        if asist_actuales and asist_iniciales:
            delta_asistencia = np.mean(asist_actuales) - np.mean(asist_iniciales)
        else:
            delta_asistencia = 0.0

    # --- IEA con penalización por sobregiro ---
    iea = calcular_iea(gasto_total, horas_totales, delta_rendimiento,
                       delta_asistencia, accion.presupuesto_asignado)

    # --- Pearson: horas vs mejora de nota ---
    r_pearson, _ = calcular_correlacion_pearson(x_horas, y_deltas)

    # --- Proyección: serie temporal del promedio grupal (con mes real como X) ---
    periodos = sorted({
        r.periodo for est_id in estudiante_ids
        for r in RegistroAppPonderado.query.filter_by(estudiante_id=est_id).all()
    })
    serie, meses_x = [], []
    for per in periodos:
        notas_per = [n for n in (_nota_promedio(e, per) for e in estudiante_ids) if n is not None]
        if notas_per:
            serie.append(float(np.mean(notas_per)))
            try:
                meses_x.append(int(per.split("-")[1]))
            except (ValueError, IndexError):
                meses_x.append(len(serie))

    proyeccion = proyectar_cumplimiento(serie, accion.meta_valor, x_indices=meses_x)
    semaforo = determinar_semaforo(proyeccion)

    # --- Upsert en IndicadorAccion ---
    indicador = IndicadorAccion.query.filter_by(accion_id=accion_id, mes=periodo).first()
    if not indicador:
        indicador = IndicadorAccion(accion_id=accion_id, mes=periodo)

    indicador.iea = iea
    indicador.correlacion_pearson = r_pearson
    indicador.proyeccion_cumplimiento = proyeccion
    indicador.estado_semaforo = semaforo
    indicador.gasto_mes = gasto_total

    db.session.add(indicador)
    db.session.commit()
    return indicador

# Primero actualiza el import superior para incluir Estudiante:
# from app.models.metrics import RegistroAppPonderado, ParticipacionAccion, IndicadorAccion, Estudiante


def obtener_impacto_individual(accion_id):
    """Devuelve el impacto individual de cada alumno participante en la acción.

    Para cada alumno: horas acumuladas, nota inicial, nota actual,
    delta de mejora, asistencia y clasificación.
    """
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return []

    participaciones = ParticipacionAccion.query.filter_by(accion_id=accion_id).all()

    # Acumular horas por estudiante (si participó varias veces, se suman)
    horas_por_est = {}
    for p in participaciones:
        horas_por_est[p.estudiante_id] = horas_por_est.get(p.estudiante_id, 0) + p.horas_asistencia

    resultado = []
    for est_id, horas in horas_por_est.items():
        estudiante = Estudiante.query.get(est_id)
        if not estudiante:
            continue

        # --- Nota inicial (periodo más antiguo) ---
        periodo_inicial = _primer_periodo(est_id)
        nota_inicial = _nota_promedio(est_id, periodo_inicial) if periodo_inicial else None

        # --- Nota actual (periodo más reciente con datos) ---
        reg_reciente = RegistroAppPonderado.query.filter_by(estudiante_id=est_id)\
            .order_by(RegistroAppPonderado.periodo.desc()).first()
        periodo_reciente = reg_reciente.periodo if reg_reciente else None
        nota_actual = _nota_promedio(est_id, periodo_reciente) if periodo_reciente else None

        # Si el alumno solo tiene un periodo registrado, comparamos contra la línea base
        if periodo_reciente and periodo_reciente == periodo_inicial:
            nota_inicial = accion.linea_base_valor if accion.linea_base_valor is not None else 0.0

        # --- Asistencias ---
        asist_inicial = _asistencia_promedio(est_id, periodo_inicial) if periodo_inicial else None
        asist_actual = _asistencia_promedio(est_id, periodo_reciente) if periodo_reciente else None

        # --- Deltas ---
        delta = round(nota_actual - nota_inicial, 2) if (nota_actual is not None and nota_inicial is not None) else None
        delta_asist = round(asist_actual - asist_inicial, 1) if (asist_actual is not None and asist_inicial is not None) else None

        # --- Clasificación individual ---
        if delta is None:
            clasificacion, clase = "Sin datos", "bg-gray-100 text-gray-600"
        elif delta >= 0.3:
            clasificacion, clase = "Mejora alta", "bg-green-100 text-green-700"
        elif delta >= 0.1:
            clasificacion, clase = "Mejora leve", "bg-cyan-100 text-cyan-700"
        elif delta >= -0.1:
            clasificacion, clase = "Estable", "bg-gray-100 text-gray-600"
        else:
            clasificacion, clase = "Retroceso", "bg-red-100 text-red-700"

        resultado.append({
            "id": estudiante.id,
            "nombre": estudiante.nombre_completo,
            "curso": estudiante.curso.nombre if estudiante.curso else "N/A",
            "horas": horas,
            "nota_inicial": round(nota_inicial, 2) if nota_inicial is not None else None,
            "nota_actual": round(nota_actual, 2) if nota_actual is not None else None,
            "delta": delta,
            "asistencia_actual": round(asist_actual, 1) if asist_actual is not None else None,
            "delta_asistencia": delta_asist,
            "clasificacion": clasificacion,
            "clase": clase,
        })

    # Ordenar por horas descendente (para ver la relación horas-mejora de arriba a abajo)
    resultado.sort(key=lambda x: x["horas"], reverse=True)
    return resultado
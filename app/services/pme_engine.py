"""Motor algorítmico de cálculo cuantitativo PME.

Incluye:
- Índice de Eficiencia de Acción (IEA) con escalas normalizadas y penalización por sobregiro
- Correlación de Pearson (horas vs mejora/progreso)
- Algoritmo de Semáforo / Proyección de Cumplimiento
- Índice de Progreso de Indicador (MAYOR_ES_MEJOR / MENOR_ES_MEJOR)
- Índice de Progreso de la Acción (IPA) para múltiples indicadores
"""
import numpy as np
from app.extensions import db
from app.models.metrics import (RegistroAppPonderado, ParticipacionAccion,
                                 IndicadorAccion, Estudiante,
                                 DefinicionIndicador, MedicionIndicador)
from app.models.pme import AccionPME, ConfiguracionSistema


# ============================================================
# FUNCIONES MATEMÁTICAS PURAS
# ============================================================

def calcular_progreso_indicador(linea_base, valor_actual, meta, direccion="MAYOR_ES_MEJOR"):
    """Calcula progreso hacia meta con dirección configurable.

    Args:
        linea_base: Valor inicial del estudiante o grupo.
        valor_actual: Valor actual medido.
        meta: Valor objetivo.
        direccion: "MAYOR_ES_MEJOR" o "MENOR_ES_MEJOR".

    Returns:
        dict con: delta, progreso_meta (%), cumplimiento (%), estado
    """
    if linea_base is None or valor_actual is None or meta is None:
        return {"delta": None, "progreso_meta": None, "cumplimiento": None, "estado": "SIN_DATOS"}

    linea_base = float(linea_base)
    valor_actual = float(valor_actual)
    meta = float(meta)
    delta = valor_actual - linea_base

    # Caso: línea base igual a meta (sin brecha)
    if linea_base == meta:
        cumplimiento = (valor_actual / meta * 100) if meta != 0 else 0.0
        if valor_actual == meta:
            estado = "SIN_BRECHA"
        elif valor_actual > meta:
            estado = "META_ALCANZADA"
        else:
            estado = "RETROCESO"
        return {"delta": round(delta, 4), "progreso_meta": 0.0,
                "cumplimiento": round(cumplimiento, 2), "estado": estado}

    # Cálculo según dirección
    if direccion == "MAYOR_ES_MEJOR":
        if linea_base >= meta:
            cumplimiento = (valor_actual / meta * 100) if meta != 0 else 0.0
            return {"delta": round(delta, 4), "progreso_meta": None,
                    "cumplimiento": round(cumplimiento, 2), "estado": "META_ALCANZADA"}
        progreso = (valor_actual - linea_base) / (meta - linea_base)
    else:  # MENOR_ES_MEJOR
        if linea_base <= meta:
            cumplimiento = (meta / valor_actual * 100) if valor_actual != 0 else 0.0
            return {"delta": round(delta, 4), "progreso_meta": None,
                    "cumplimiento": round(cumplimiento, 2), "estado": "META_ALCANZADA"}
        progreso = (linea_base - valor_actual) / (linea_base - meta)

    cumplimiento = (valor_actual / meta * 100) if meta != 0 else 0.0

    if progreso < 0:
        estado = "RETROCESO"
    elif progreso == 0:
        estado = "ESTABLE"
    elif progreso >= 1:
        estado = "META_ALCANZADA"
    else:
        estado = "EN_PROGRESO"

    return {"delta": round(delta, 4), "progreso_meta": round(progreso * 100, 2),
            "cumplimiento": round(cumplimiento, 2), "estado": estado}


def calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia,
                 presupuesto_asignado=None, peso_rendimiento=0.6, peso_asistencia=0.4):
    """Calcula el Índice de Eficiencia de Acción (IEA) con pesos configurables."""
    if gasto_ejecutado <= 0 or horas_ejecutadas <= 0:
        return 0.0
    delta_rend_norm = max(-2.0, min(2.0, delta_rendimiento))
    delta_asist_norm = max(-10.0, min(10.0, delta_asistencia)) / 10.0
    total_pesos = peso_rendimiento + peso_asistencia
    if total_pesos <= 0:
        total_pesos = 1.0
    impacto = (delta_rend_norm * peso_rendimiento + delta_asist_norm * peso_asistencia) / total_pesos
    recurso = (gasto_ejecutado / 1_000_000) + (horas_ejecutadas / 10)
    if recurso <= 0:
        return 0.0
    iea = (impacto / recurso) * 10
    if presupuesto_asignado and presupuesto_asignado > 0:
        if gasto_ejecutado > presupuesto_asignado:
            iea *= presupuesto_asignado / gasto_ejecutado
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
    """Proyección de cumplimiento a fin de año (noviembre = índice 11)."""
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
    """Promedio de TODAS las notas del estudiante en un periodo."""
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


def _horas_por_estudiante(accion_id):
    """Acumula horas de participación por estudiante (múltiples cargas se suman)."""
    parts = ParticipacionAccion.query.filter_by(accion_id=accion_id).all()
    horas = {}
    for p in parts:
        horas[p.estudiante_id] = horas.get(p.estudiante_id, 0) + p.horas_asistencia
    return horas


# ============================================================
# ORQUESTADOR PRINCIPAL
# ============================================================

def procesar_indicadores_accion(accion_id, periodo):
    """Dispatcher: detecta modelo nuevo (DefinicionIndicador) vs legacy."""
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return None
    definiciones = DefinicionIndicador.query.filter_by(
        accion_id=accion_id, activo=True
    ).all()
    if definiciones:
        return _procesar_nuevo_modelo(accion, definiciones, periodo)
    return _procesar_legacy(accion, periodo)


def _procesar_legacy(accion, periodo):
    """Flujo original: IEA + Pearson notas/asistencia + proyección + semáforo."""
    horas_por_est = _horas_por_estudiante(accion.id)
    if not horas_por_est:
        return None

    est_ids = list(horas_por_est.keys())
    horas_totales = sum(horas_por_est.values())
    gasto_total = accion.presupuesto_ejecutado

    x_horas, y_deltas = [], []
    notas_actuales, asist_actuales, asist_iniciales = [], [], []

    for est_id in est_ids:
        nota_actual = _nota_promedio(est_id, periodo)
        if nota_actual is None:
            continue
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

    # Deltas del grupo
    if accion.indicador_tipo == "Asistencia":
        delta_rendimiento = 0.0
        base_asist = np.mean(asist_iniciales) if asist_iniciales else (accion.linea_base_valor or 0)
        delta_asistencia = np.mean(asist_actuales) - base_asist
    else:
        delta_rendimiento = np.mean(notas_actuales) - (accion.linea_base_valor or 0)
        delta_asistencia = (np.mean(asist_actuales) - np.mean(asist_iniciales)) if (asist_actuales and asist_iniciales) else 0.0

    # Configuración
    config = ConfiguracionSistema.query.first()
    peso_r = config.peso_rendimiento if config else 0.6
    peso_a = config.peso_asistencia if config else 0.4
    um_rojo = config.umbral_rojo if config else 0.85
    um_amar = config.umbral_amarillo if config else 0.95

    # IEA
    iea = calcular_iea(gasto_total, horas_totales, delta_rendimiento, delta_asistencia,
                       accion.presupuesto_asignado, peso_rendimiento=peso_r, peso_asistencia=peso_a)

    # Pearson: horas vs delta nota
    r_pearson, _ = calcular_correlacion_pearson(x_horas, y_deltas)

    # Proyección: serie temporal del promedio grupal
    periodos = sorted({r.periodo for est_id in est_ids
                       for r in RegistroAppPonderado.query.filter_by(estudiante_id=est_id).all()})
    serie, meses_x = [], []
    for per in periodos:
        notas_per = [n for n in (_nota_promedio(e, per) for e in est_ids) if n is not None]
        if notas_per:
            serie.append(float(np.mean(notas_per)))
            try:
                meses_x.append(int(per.split("-")[1]))
            except (ValueError, IndexError):
                meses_x.append(len(serie))

    proyeccion = proyectar_cumplimiento(serie, accion.meta_valor, x_indices=meses_x)
    semaforo = determinar_semaforo(proyeccion, um_rojo, um_amar)

    # Upsert
    indicador = IndicadorAccion.query.filter_by(accion_id=accion.id, mes=periodo).first()
    if not indicador:
        indicador = IndicadorAccion(accion_id=accion.id, mes=periodo)
    indicador.iea = iea
    indicador.correlacion_pearson = r_pearson
    indicador.proyeccion_cumplimiento = proyeccion
    indicador.estado_semaforo = semaforo
    indicador.gasto_mes = gasto_total
    db.session.add(indicador)
    db.session.commit()
    return indicador


def _procesar_nuevo_modelo(accion, definiciones, periodo):
    """Flujo nuevo: progreso + IPA + Pearson progreso + proyección + semáforo."""
    horas_por_est = _horas_por_estudiante(accion.id)
    if not horas_por_est:
        return None

    est_ids = list(horas_por_est.keys())
    gasto_total = accion.presupuesto_ejecutado

    # Pre-cargar TODAS las mediciones de los indicadores de esta acción (1 sola query)
    def_ids = [d.id for d in definiciones]
    todas_meds = MedicionIndicador.query.filter(
        MedicionIndicador.indicador_def_id.in_(def_ids)
    ).all()
    meds_map = {}
    for m in todas_meds:
        meds_map[(m.indicador_def_id, m.estudiante_id, m.periodo)] = m

    # Procesar cada indicador definido
    resultados = []
    for definicion in definiciones:
        progresos, deltas, x_horas = [], [], []
        for est_id in est_ids:
            med = meds_map.get((definicion.id, est_id, periodo))
            if not med:
                continue
            res = calcular_progreso_indicador(
                definicion.linea_base, med.valor, definicion.meta, definicion.direccion
            )
            if res["progreso_meta"] is not None:
                progresos.append(res["progreso_meta"])
                deltas.append(res["delta"])
                x_horas.append(horas_por_est[est_id])
        if progresos:
            resultados.append({
                "def": definicion, "progresos": progresos, "deltas": deltas,
                "x_horas": x_horas, "promedio": float(np.mean(progresos))
            })

    if not resultados:
        return None

    # IPA: promedio ponderado de progreso por indicador
    total_peso = sum(r["def"].peso for r in resultados) or 1.0
    ipa = sum(r["promedio"] * r["def"].peso for r in resultados) / total_peso

    # Estadísticas grupales
    todos_prog = [p for r in resultados for p in r["progresos"]]
    todos_delta = [d for r in resultados for d in r["deltas"]]
    n_total = len(todos_prog)
    prog_promedio = float(np.mean(todos_prog))
    delta_promedio = float(np.mean(todos_delta))
    pct_mejora = round(sum(1 for p in todos_prog if p > 0) / n_total * 100, 1) if n_total else 0
    pct_meta = round(sum(1 for p in todos_prog if p >= 100) / n_total * 100, 1) if n_total else 0
    pct_retroceso = round(sum(1 for p in todos_prog if p < 0) / n_total * 100, 1) if n_total else 0

    # Pearson: horas vs progreso (indicador con más datos)
    mejor = max(resultados, key=lambda r: len(r["progresos"]))
    r_pearson, _ = calcular_correlacion_pearson(mejor["x_horas"], mejor["progresos"])

    # Proyección: serie temporal de progreso del indicador principal
    ind_ppal = resultados[0]["def"]
    periodos_unicos = sorted(set(
        m.periodo for m in todas_meds if m.indicador_def_id == ind_ppal.id
    ))
    serie, meses_x = [], []
    for per in periodos_unicos:
        vals = []
        for est_id in est_ids:
            med = meds_map.get((ind_ppal.id, est_id, per))
            if med:
                res = calcular_progreso_indicador(
                    ind_ppal.linea_base, med.valor, ind_ppal.meta, ind_ppal.direccion
                )
                if res["progreso_meta"] is not None:
                    vals.append(res["progreso_meta"])
        if vals:
            serie.append(float(np.mean(vals)))
            try:
                meses_x.append(int(per.split("-")[1]))
            except (ValueError, IndexError):
                meses_x.append(len(serie))

    # Proyección: meta = 100% (progreso completo)
    proyeccion = proyectar_cumplimiento(serie, 100.0, x_indices=meses_x)

    # Configuración
    config = ConfiguracionSistema.query.first()
    um_rojo = config.umbral_rojo if config else 0.85
    um_amar = config.umbral_amarillo if config else 0.95
    peso_r = config.peso_rendimiento if config else 0.6
    peso_a = config.peso_asistencia if config else 0.4
    semaforo = determinar_semaforo(proyeccion, um_rojo, um_amar)

    # IEA: IPA como impacto pedagógico (IPA/100 para escala compatible)
    iea = calcular_iea(gasto_total, sum(horas_por_est.values()), ipa / 100.0, 0.0,
                       accion.presupuesto_asignado, peso_rendimiento=peso_r, peso_asistencia=peso_a)

    # Upsert con campos nuevos
    indicador = IndicadorAccion.query.filter_by(accion_id=accion.id, mes=periodo).first()
    if not indicador:
        indicador = IndicadorAccion(accion_id=accion.id, mes=periodo)
    indicador.iea = iea
    indicador.correlacion_pearson = r_pearson
    indicador.proyeccion_cumplimiento = proyeccion
    indicador.estado_semaforo = semaforo
    indicador.gasto_mes = gasto_total
    indicador.ipa = round(ipa, 2)
    indicador.progreso_promedio = round(prog_promedio, 2)
    indicador.delta_promedio = round(delta_promedio, 4)
    indicador.porcentaje_mejora = pct_mejora
    indicador.porcentaje_meta_alcanzada = pct_meta
    indicador.porcentaje_retroceso = pct_retroceso
    db.session.add(indicador)
    db.session.commit()
    return indicador


def obtener_impacto_individual(accion_id):
    """Devuelve el impacto individual de cada alumno participante en la acción.

    Para cada alumno: horas acumuladas, nota inicial, nota actual,
    delta de mejora, asistencia y clasificación.
    """
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return []

    horas_por_est = _horas_por_estudiante(accion_id)
    resultado = []

    for est_id, horas in horas_por_est.items():
        estudiante = Estudiante.query.get(est_id)
        if not estudiante:
            continue

        # Nota inicial (periodo más antiguo)
        periodo_inicial = _primer_periodo(est_id)
        nota_inicial = _nota_promedio(est_id, periodo_inicial) if periodo_inicial else None

        # Nota actual (periodo más reciente)
        reg_reciente = RegistroAppPonderado.query.filter_by(estudiante_id=est_id)\
            .order_by(RegistroAppPonderado.periodo.desc()).first()
        periodo_reciente = reg_reciente.periodo if reg_reciente else None
        nota_actual = _nota_promedio(est_id, periodo_reciente) if periodo_reciente else None

        # Si solo tiene un periodo, comparar contra línea base
        if periodo_reciente and periodo_reciente == periodo_inicial:
            nota_inicial = accion.linea_base_valor if accion.linea_base_valor is not None else 0.0

        # Asistencias
        asist_inicial = _asistencia_promedio(est_id, periodo_inicial) if periodo_inicial else None
        asist_actual = _asistencia_promedio(est_id, periodo_reciente) if periodo_reciente else None

        # Deltas
        delta = round(nota_actual - nota_inicial, 2) if (nota_actual is not None and nota_inicial is not None) else None
        delta_asist = round(asist_actual - asist_inicial, 1) if (asist_actual is not None and asist_inicial is not None) else None

        # Clasificación
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
            "id": estudiante.id, "nombre": estudiante.nombre_completo,
            "curso": estudiante.curso.nombre if estudiante.curso else "N/A",
            "horas": horas,
            "nota_inicial": round(nota_inicial, 2) if nota_inicial is not None else None,
            "nota_actual": round(nota_actual, 2) if nota_actual is not None else None,
            "delta": delta,
            "asistencia_actual": round(asist_actual, 1) if asist_actual is not None else None,
            "delta_asistencia": delta_asist,
            "clasificacion": clasificacion, "clase": clase,
        })

    resultado.sort(key=lambda x: x["horas"], reverse=True)
    return resultado

def obtener_impacto_individual_nuevo(accion_id):
    """Impacto individual para acciones con modelo nuevo (DefinicionIndicador).

    Para cada alumno devuelve horas acumuladas y progreso por cada indicador
    definido en la acción, más un progreso promedio y estado grupal.
    """
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return []

    definiciones = DefinicionIndicador.query.filter_by(
        accion_id=accion_id, activo=True
    ).all()
    if not definiciones:
        return []

    horas_por_est = _horas_por_estudiante(accion_id)
    resultado = []

    for est_id, horas in horas_por_est.items():
        estudiante = Estudiante.query.get(est_id)
        if not estudiante:
            continue

        indicadores_data = []
        for def_ind in definiciones:
            med = MedicionIndicador.query.filter_by(
                indicador_def_id=def_ind.id, estudiante_id=est_id
            ).order_by(MedicionIndicador.periodo.desc()).first()

            if med:
                res = calcular_progreso_indicador(
                    def_ind.linea_base, med.valor, def_ind.meta, def_ind.direccion
                )
                indicadores_data.append({
                    "indicador_id": def_ind.id,
                    "indicador_nombre": def_ind.nombre,
                    "unidad": def_ind.unidad_medida or "",
                    "direccion": def_ind.direccion,
                    "linea_base": def_ind.linea_base,
                    "meta": def_ind.meta,
                    "valor_actual": med.valor,
                    "periodo": med.periodo,
                    "delta": res["delta"],
                    "progreso": res["progreso_meta"],
                    "cumplimiento": res["cumplimiento"],
                    "estado": res["estado"],
                })

        progresos = [i["progreso"] for i in indicadores_data if i["progreso"] is not None]
        prog_promedio = round(float(np.mean(progresos)), 2) if progresos else None

        if not indicadores_data:
            estado_grupal = "SIN_DATOS"
        elif prog_promedio is not None:
            if prog_promedio >= 100:
                estado_grupal = "META_ALCANZADA"
            elif prog_promedio > 0:
                estado_grupal = "EN_PROGRESO"
            elif prog_promedio == 0:
                estado_grupal = "ESTABLE"
            else:
                estado_grupal = "RETROCESO"
        else:
            estado_grupal = "SIN_DATOS"

        resultado.append({
            "id": estudiante.id,
            "nombre": estudiante.nombre_completo,
            "curso": estudiante.curso.nombre if estudiante.curso else "N/A",
            "horas": horas,
            "indicadores": indicadores_data,
            "progreso_promedio": prog_promedio,
            "estado_grupal": estado_grupal,
        })

    resultado.sort(key=lambda x: x["horas"], reverse=True)
    return resultado
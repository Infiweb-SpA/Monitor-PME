"""Motor algorítmico de cálculo cuantitativo PME.

Incluye:
- Índice de Eficiencia de Acción (IEA)
- Correlación de Pearson
- Algoritmo de Semáforo / Proyección de Cumplimiento
- Orquestador de Base de Datos (procesar_indicadores_accion)
"""
import numpy as np
from app.extensions import db
from app.models.pme import AccionPME
from app.models.metrics import RegistroAppPonderado, ParticipacionAccion, IndicadorAccion


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
    """Calcula el coeficiente de correlación de Pearson entre dos arrays."""
    if len(x) < 2 or len(y) < 2 or len(x) != len(y):
        return None, None
    try:
        # Usamos numpy para evitar la dependencia pesada de scipy en esta etapa
        r = np.corrcoef(x, y)[0, 1]
        if np.isnan(r):
            return None, None
        return round(float(r), 3), 0.0 # Retornamos 0.0 en p-value por simplicidad
    except Exception:
        return None, None


def determinar_semaforo(proyeccion_cumplimiento, umbral_rojo=0.85, umbral_amarillo=0.95):
    """Determina el estado del semáforo según proyección de cumplimiento."""
    if proyeccion_cumplimiento < umbral_rojo:
        return "Rojo"
    elif proyeccion_cumplimiento < umbral_amarillo:
        return "Amarillo"
    return "Verde"


def proyectar_cumplimiento(valores_historicos, meta):
    """Proyecta el cumplimiento a fin de año usando regresión lineal simple."""
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


def procesar_indicadores_accion(accion_id, periodo):
    """Orquestador que une la base de datos con el motor algorítmico."""
    accion = AccionPME.query.get(accion_id)
    if not accion:
        return None

    # 1. Obtener estudiantes participantes y sus horas
    participaciones = ParticipacionAccion.query.filter_by(accion_id=accion_id).all()
    if not participaciones:
        return None

    estudiante_ids = [p.estudiante_id for p in participaciones]
    horas_totales = sum(p.horas_asistencia for p in participaciones)
    gasto_total = accion.presupuesto_ejecutado

    # 2. Obtener registros de App Ponderado del período actual para esos estudiantes
    registros_actual = RegistroAppPonderado.query.filter(
        RegistroAppPonderado.estudiante_id.in_(estudiante_ids),
        RegistroAppPonderado.periodo == periodo
    ).all()

    if not registros_actual:
        return None

    # 3. Preparar arrays para cálculos
    promedio_notas_actual = np.mean([r.promedio_notas for r in registros_actual])
    promedio_asist_actual = np.mean([r.porcentaje_asistencia for r in registros_actual])
    
    delta_rendimiento = promedio_notas_actual - (accion.linea_base_valor if accion.indicador_tipo == "Promedio Notas" else 0)
    delta_asistencia = promedio_asist_actual - (accion.linea_base_valor if accion.indicador_tipo == "Asistencia" else 0)

    # Arrays para Pearson: X = Horas, Y = Mejora en la nota (Delta)
    x_horas = []
    y_delta_notas = []
    
    for p in participaciones:
        reg_actual = next((r for r in registros_actual if r.estudiante_id == p.estudiante_id), None)
        if reg_actual:
            # Buscar la nota más antigua del alumno para calcular la mejora real
            reg_inicial = RegistroAppPonderado.query.filter(
                RegistroAppPonderado.estudiante_id == p.estudiante_id
            ).order_by(RegistroAppPonderado.periodo.asc()).first()
            
            if reg_inicial and reg_inicial.id != reg_actual.id:
                # Si hay histórico, el delta es la diferencia entre la nota actual y la inicial
                delta_nota = reg_actual.promedio_notas - reg_inicial.promedio_notas
            else:
                # Si solo hay un periodo, comparamos contra la línea base de la acción
                delta_nota = reg_actual.promedio_notas - (accion.linea_base_valor or 0)
            
            x_horas.append(p.horas_asistencia)
            y_delta_notas.append(delta_nota)

    # 4. Ejecutar matemáticas
    iea = calcular_iea(gasto_total, horas_totales, delta_rendimiento, delta_asistencia)
    r_pearson, _ = calcular_correlacion_pearson(x_horas, y_delta_notas) # ¡Ahora correlaciona horas vs mejora!
    
    # Proyección basada en los promedios históricos
    valores_historicos = [r.promedio_notas for r in registros_actual]
    proyeccion = proyectar_cumplimiento(valores_historicos, accion.meta_valor)
    semaforo = determinar_semaforo(proyeccion)

    # 5. Guardar en la tabla IndicadorAccion
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
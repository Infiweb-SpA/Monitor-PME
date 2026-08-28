"""Blueprint del dashboard ejecutivo."""
import numpy as np
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models.pme import AccionPME, DimensionPME
from app.models.metrics import IndicadorAccion, DefinicionIndicador
from sqlalchemy import func
from app.extensions import db

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    """Cuadro de mando ejecutivo con resumen global y alertas."""

    # 1. Presupuesto global
    total_asignado = db.session.query(func.sum(AccionPME.presupuesto_asignado)).scalar() or 0.0
    total_ejecutado = db.session.query(func.sum(AccionPME.presupuesto_ejecutado)).scalar() or 0.0
    porcentaje_global = (total_ejecutado / total_asignado * 100) if total_asignado > 0 else 0.0

    # 2. Acciones activas + último indicador de cada una
    acciones = AccionPME.query.filter(
        AccionPME.estado.in_(["Planificada", "En Ejecución"])
    ).all()

    alertas = []
    semaforo = {"Verde": 0, "Amarillo": 0, "Rojo": 0, "Sin Datos": 0}

    ieas, ipas, progresos = [], [], []
    pct_mejoras, pct_metas, pct_retrocesos = [], [], []
    acciones_detalle = []
    latest_map = {}

    for acc in acciones:
        ind = acc.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        latest_map[acc.id] = ind
        estado = ind.estado_semaforo if ind else "Sin Datos"

        if estado in semaforo:
            semaforo[estado] += 1

        if estado in ("Rojo", "Amarillo"):
            alertas.append({
                "accion": acc.nombre, "estado": estado,
                "iea": ind.iea if ind else None,
                "proyeccion": ind.proyeccion_cumplimiento if ind else None,
                "ipa": ind.ipa if ind else None,
            })

        if ind:
            for val, lst in [(ind.iea, ieas), (ind.ipa, ipas),
                             (ind.progreso_promedio, progresos),
                             (ind.porcentaje_mejora, pct_mejoras),
                             (ind.porcentaje_meta_alcanzada, pct_metas),
                             (ind.porcentaje_retroceso, pct_retrocesos)]:
                if val is not None:
                    lst.append(val)

        tiene_nuevos = DefinicionIndicador.query.filter_by(
            accion_id=acc.id, activo=True
        ).count() > 0

        acciones_detalle.append({
            "nombre": acc.nombre, "estado": estado,
            "iea": ind.iea if ind else None,
            "proyeccion": ind.proyeccion_cumplimiento if ind else None,
            "ipa": ind.ipa if ind else None,
            "progreso": ind.progreso_promedio if ind else None,
            "es_nuevo": tiene_nuevos,
        })

    # 3. Promedios globales
    def avg(lst):
        return round(float(np.mean(lst)), 2) if lst else None

    # 4. Progreso por dimensión
    dim_data = []
    for dim in DimensionPME.query.order_by(DimensionPME.orden).all():
        dim_ipas = []
        for obj in dim.objetivos.all():
            for a in obj.acciones.all():
                ind = latest_map.get(a.id)
                if ind and ind.ipa is not None:
                    dim_ipas.append(ind.ipa)
        dim_data.append({
            "nombre": dim.nombre,
            "progreso": round(float(np.mean(dim_ipas)), 1) if dim_ipas else None,
            "count": len(dim_ipas),
        })

    has_dim_data = any(d["progreso"] is not None for d in dim_data)

    return render_template("dashboard/index.html",
        total_asignado=total_asignado, total_ejecutado=total_ejecutado,
        porcentaje_global=round(porcentaje_global, 1),
        alertas=alertas, grafico_semaforo=semaforo,
        iea_promedio=avg(ieas), ipas_count=len(ipas),
        ipa_promedio=avg(ipas), progreso_promedio=avg(progresos),
        pct_mejora_promedio=avg(pct_mejoras),
        pct_meta_promedio=avg(pct_metas),
        pct_retroceso_promedio=avg(pct_retrocesos),
        dimensiones_data=dim_data, has_dim_data=has_dim_data,
        acciones_detalle=acciones_detalle,
    )


@dashboard_bp.route("/api/datos-grafico")
@login_required
def datos_grafico():
    """Endpoint JSON opcional para Chart.js vía AJAX."""
    acciones = AccionPME.query.all()
    return jsonify({
        "labels": [a.nombre for a in acciones],
        "data_presupuesto": [a.presupuesto_ejecutado for a in acciones]
    })
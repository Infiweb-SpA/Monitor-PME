"""Blueprint del dashboard ejecutivo."""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models.pme import AccionPME
from app.models.metrics import IndicadorAccion
from sqlalchemy import func
from app.extensions import db

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    """Cuadro de mando ejecutivo con resumen global y alertas."""
    
    # 1. Resumen Global de Presupuesto
    total_asignado = db.session.query(func.sum(AccionPME.presupuesto_asignado)).scalar() or 0.0
    total_ejecutado = db.session.query(func.sum(AccionPME.presupuesto_ejecutado)).scalar() or 0.0
    porcentaje_ejecucion_global = (total_ejecutado / total_asignado * 100) if total_asignado > 0 else 0.0

    # 2. Alertas Tempranas (Semáforos)
    # Obtenemos el indicador más reciente de cada acción
    acciones = AccionPME.query.filter(AccionPME.estado.in_(["Planificada", "En Ejecución"])).all()
    
    alertas = []
    datos_grafico_semaforo = {"Verde": 0, "Amarillo": 0, "Rojo": 0, "Sin Datos": 0}
    
    for accion in acciones:
        indicador = accion.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        estado = indicador.estado_semaforo if indicador else "Sin Datos"
        
        if estado in datos_grafico_semaforo:
            datos_grafico_semaforo[estado] += 1
            
        if estado in ["Rojo", "Amarillo"]:
            alertas.append({
                "accion": accion.nombre,
                "estado": estado,
                "iea": indicador.iea if indicador else None,
                "proyeccion": indicador.proyeccion_cumplimiento if indicador else None
            })

    # 3. Datos para pasar a la vista
    contexto = {
        "total_asignado": total_asignado,
        "total_ejecutado": total_ejecutado,
        "porcentaje_global": round(porcentaje_ejecucion_global, 1),
        "alertas": alertas,
        "grafico_semaforo": datos_grafico_semaforo
    }

    return render_template("dashboard/index.html", **contexto)


@dashboard_bp.route("/api/datos-grafico")
@login_required
def datos_grafico():
    """Endpoint JSON opcional para alimentar Chart.js dinámicamente vía AJAX."""
    # Aquí podrías poner lógica más granular si los gráficos necesitan actualizarse sin recargar
    acciones = AccionPME.query.all()
    labels = [a.nombre for a in acciones]
    data_presupuesto = [a.presupuesto_ejecutado for a in acciones]
    
    return jsonify({
        "labels": labels,
        "data_presupuesto": data_presupuesto
    })
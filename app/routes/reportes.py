"""Blueprint de reportes y exportación."""
import io
import pandas as pd
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required
from app.models.pme import AccionPME, DimensionPME
from app.models.metrics import IndicadorAccion
from app.extensions import db

reportes_bp = Blueprint("reportes", __name__, template_folder="../templates/reportes")


@reportes_bp.route("/")
@login_required
def index():
    """Listado de reportes disponibles y vista previa."""
    # Mostrar resumen rápido de acciones para reporte en pantalla
    acciones = AccionPME.query.order_by(AccionPME.estado).all()
    dimensiones = DimensionPME.query.order_by(DimensionPME.orden).all()
    return render_template("reportes/index.html", acciones=acciones, dimensiones=dimensiones)


@reportes_bp.route("/exportar_excel")
@login_required
def exportar_excel():
    """Genera y descarga un archivo Excel con el consolidado del PME."""
    
    # Consultamos todas las acciones
    acciones = AccionPME.query.all()
    data = []
    
    for accion in acciones:
        # Buscamos el último indicador calculado para esa acción
        indicador = accion.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        
        data.append({
            "Dimensión": accion.objetivo.dimension.nombre if accion.objetivo else "N/A",
            "Nombre Acción": accion.nombre,
            "Estado": accion.estado,
            "Responsable": accion.responsable or "No asignado",
            "Presupuesto Asignado ($)": accion.presupuesto_asignado,
            "Presupuesto Ejecutado ($)": accion.presupuesto_ejecutado,
            "% Ejecución Presupuestaria": round(accion.porcentaje_ejecucion_presupuesto(), 2),
            "Línea Base": accion.linea_base_valor,
            "Meta Valor": accion.meta_valor,
            "Indicador Tipo": accion.indicador_tipo or "N/A",
            "IEA (Eficiencia)": indicador.iea if indicador else None,
            "Correlación Pearson": indicador.correlacion_pearson if indicador else None,
            "Proyección Cumplimiento": indicador.proyeccion_cumplimiento if indicador else None,
            "Semáforo Alerta": indicador.estado_semaforo if indicador else "Sin Datos"
        })
    
    if not data:
        flash("No hay acciones PME registradas para exportar.", "warning")
        return redirect(url_for("reportes.index"))
        
    # Crear DataFrame de Pandas
    df = pd.DataFrame(data)
    
    # Escribir el Excel en memoria (BytesIO) para no guardar archivos en el servidor
    output = io.BytesIO()
    # Necesitas 'openpyxl' instalado (pip install openpyxl) - suele venir con pandas
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte PME')
    
    output.seek(0)
    
    # Forzar descarga en el navegador
    return send_file(
        output,
        download_name='Reporte_PME_EduGest.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
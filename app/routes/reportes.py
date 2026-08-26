"""Blueprint de reportes y exportación."""
import io
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import func
import pandas as pd
from app.extensions import db
from app.models.pme import AccionPME, ObjetivoPME, DimensionPME, Establecimiento, Curso
from app.models.metrics import (
    IndicadorAccion, ParticipacionAccion, MetricaSIGE, Estudiante
)

reportes_bp = Blueprint("reportes", __name__, template_folder="../templates/reportes")


# ============================================================
# HELPERS
# ============================================================

def _df_acciones(acciones):
    """Construye el DataFrame de la Matriz de Rendición a partir de una lista de acciones."""
    data = []
    for accion in acciones:
        indicador = accion.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        data.append({
            "Código": accion.codigo_interno or "N/A",
            "Dimensión": accion.objetivo.dimension.nombre if accion.objetivo and accion.objetivo.dimension else "N/A",
            "Nombre Acción": accion.nombre,
            "Descripción": accion.descripcion or "",
            "Estado": accion.estado,
            "Responsable": accion.responsable or "No asignado",
            "Fuente Financiamiento": accion.fuente_financiamiento or "N/A",
            "Presupuesto Asignado ($)": accion.presupuesto_asignado,
            "Presupuesto Ejecutado ($)": accion.presupuesto_ejecutado,
            "% Ejecución Presupuestaria": round(accion.porcentaje_ejecucion_presupuesto(), 2),
            "Indicador Tipo": accion.indicador_tipo or "N/A",
            "Unidad de Medida": accion.unidad_medida or "N/A",
            "Línea Base": accion.linea_base_valor,
            "Meta Valor": accion.meta_valor,
            "Meta Cuantitativa": accion.meta_cuantitativa or "",
            "Justificación (Cualitativa)": accion.meta_cualitativa or "",
            "IEA (Eficiencia)": indicador.iea if indicador else None,
            "Correlación Pearson": indicador.correlacion_pearson if indicador else None,
            "Proyección Cumplimiento": indicador.proyeccion_cumplimiento if indicador else None,
            "Semáforo Alerta": indicador.estado_semaforo if indicador else "Sin Datos",
        })
    return pd.DataFrame(data)


def _estadisticas_globales(acciones):
    """Calcula KPIs globales para el reporte ejecutivo y la vista previa."""
    total_asignado = sum(a.presupuesto_asignado for a in acciones)
    total_ejecutado = sum(a.presupuesto_ejecutado for a in acciones)
    pje_ejecucion = (total_ejecutado / total_asignado * 100) if total_asignado > 0 else 0.0

    semaforos = {"Verde": 0, "Amarillo": 0, "Rojo": 0, "Sin Datos": 0}
    ieas = []
    for acc in acciones:
        ind = acc.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        estado = ind.estado_semaforo if ind else "Sin Datos"
        semaforos[estado] = semaforos.get(estado, 0) + 1
        if ind and ind.iea is not None:
            ieas.append(ind.iea)

    return {
        "total_asignado": total_asignado,
        "total_ejecutado": total_ejecutado,
        "pje_ejecucion": round(pje_ejecucion, 1),
        "semaforos": semaforos,
        "iea_promedio": round(sum(ieas) / len(ieas), 2) if ieas else None,
    }


# ============================================================
# VISTAS
# ============================================================

@reportes_bp.route("/")
@login_required
def index():
    """Panel de reportes con vista previa de datos reales."""
    acciones = AccionPME.query.all()
    dimensiones = DimensionPME.query.order_by(DimensionPME.orden).all()
    cursos = Curso.query.all()
    establecimiento = Establecimiento.query.first()
    stats = _estadisticas_globales(acciones)

    return render_template(
        "reportes/index.html",
        acciones=acciones,
        dimensiones=dimensiones,
        cursos=cursos,
        establecimiento=establecimiento,
        total_acciones=len(acciones),
        **stats,
    )


@reportes_bp.route("/ejecutivo")
@login_required
def reporte_ejecutivo():
    """Vista HTML imprimible del Reporte Ejecutivo para el Sostenedor (Guardar como PDF)."""
    establecimiento = Establecimiento.query.first()
    acciones = AccionPME.query.all()
    stats = _estadisticas_globales(acciones)

    # Filas detalladas por acción
    filas = []
    for acc in acciones:
        ind = acc.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        pje = acc.porcentaje_ejecucion_presupuesto()
        filas.append({
            "codigo": acc.codigo_interno or "N/A",
            "nombre": acc.nombre,
            "dimension": acc.objetivo.dimension.nombre if acc.objetivo and acc.objetivo.dimension else "N/A",
            "estado": acc.estado,
            "asignado": acc.presupuesto_asignado,
            "ejecutado": acc.presupuesto_ejecutado,
            "pje": round(pje, 1),
            "iea": ind.iea if ind else None,
            "pearson": ind.correlacion_pearson if ind else None,
            "proyeccion": round(ind.proyeccion_cumplimiento * 100, 1) if ind and ind.proyeccion_cumplimiento else None,
            "semaforo": ind.estado_semaforo if ind else "Sin Datos",
        })

    alertas = [f for f in filas if f["semaforo"] in ("Rojo", "Amarillo")]

    return render_template(
        "reportes/ejecutivo.html",
        establecimiento=establecimiento,
        fecha=datetime.now(),
        filas=filas,
        alertas=alertas,
        **stats,
    )


# ============================================================
# EXPORTACIONES
# ============================================================

@reportes_bp.route("/exportar_excel")
@login_required
def exportar_excel():
    """Matriz de Rendición en Excel. Acepta filtros del Reporte Personalizado por query params."""
    # --- Filtros opcionales (Reporte Personalizado) ---
    query = AccionPME.query

    dim_ids = request.args.get("dimensiones")  # formato: "1,3"
    if dim_ids:
        ids = [int(x) for x in dim_ids.split(",") if x.strip().isdigit()]
        if ids:
            query = query.join(ObjetivoPME).filter(ObjetivoPME.dimension_id.in_(ids))

    curso = request.args.get("curso")
    if curso:
        query = query.filter(AccionPME.curso_objetivo == curso)

    desde = request.args.get("desde")
    if desde:
        try:
            fi = datetime.strptime(desde, "%Y-%m-%d").date()
            query = query.filter(AccionPME.fecha_inicio >= fi)
        except ValueError:
            pass

    hasta = request.args.get("hasta")
    if hasta:
        try:
            ff = datetime.strptime(hasta, "%Y-%m-%d").date()
            query = query.filter(AccionPME.fecha_fin <= ff)
        except ValueError:
            pass

    acciones = query.order_by(AccionPME.codigo_interno).all()
    if not acciones:
        flash("No hay acciones que coincidan con los filtros seleccionados.", "warning")
        return redirect(url_for("reportes.index"))

    df = _df_acciones(acciones)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Matriz Rendición")
    output.seek(0)

    nombre = f"Matriz_Rendicion_PME_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        download_name=nombre,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reportes_bp.route("/auditoria")
@login_required
def auditoria_zip():
    """Genera un ZIP con toda la trazabilidad del PME para auditoría (Superintendencia)."""
    acciones = AccionPME.query.all()
    if not acciones:
        flash("No hay datos registrados para generar el paquete de auditoría.", "warning")
        return redirect(url_for("reportes.index"))

    buffer = io.BytesIO()
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. Matriz de Rendición (Excel)
        df_acc = _df_acciones(acciones)
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            df_acc.to_excel(writer, index=False, sheet_name="Matriz Rendición")
        excel_buf.seek(0)
        zf.writestr("01_matriz_rendicion_pme.xlsx", excel_buf.read())

        # 2. Indicadores históricos por acción y mes (CSV)
        inds = IndicadorAccion.query.join(AccionPME).order_by(AccionPME.id, IndicadorAccion.mes).all()
        df_ind = pd.DataFrame([{
            "Acción": i.accion.nombre,
            "Código": i.accion.codigo_interno or "",
            "Periodo": i.mes,
            "IEA": i.iea,
            "Correlación Pearson": i.correlacion_pearson,
            "Proyección Cumplimiento": i.proyeccion_cumplimiento,
            "Semáforo": i.estado_semaforo,
            "Gasto del Mes ($)": i.gasto_mes,
        } for i in inds])
        zf.writestr("02_indicadores_historicos.csv", df_ind.to_csv(index=False).encode("utf-8-sig"))

        # 3. Participaciones de alumnos en acciones (CSV)
        parts = (
            db.session.query(ParticipacionAccion, Estudiante, AccionPME)
            .join(Estudiante, ParticipacionAccion.estudiante_id == Estudiante.id)
            .join(AccionPME, ParticipacionAccion.accion_id == AccionPME.id)
            .all()
        )
        df_part = pd.DataFrame([{
            "Estudiante": e.nombre_completo,
            "Matrícula": e.matricula,
            "Curso": e.curso.nombre if e.curso else "",
            "Acción PME": a.nombre,
            "Código Acción": a.codigo_interno or "",
            "Horas Asistencia": p.horas_asistencia,
            "Talleres Asistidos": p.asistencia_talleres,
            "Fecha Registro": p.fecha_registro.strftime("%d/%m/%Y") if p.fecha_registro else "",
        } for p, e, a in parts])
        zf.writestr("03_participaciones_alumnos.csv", df_part.to_csv(index=False).encode("utf-8-sig"))

        # 4. Métricas oficiales SIGE (CSV)
        sige = MetricaSIGE.query.order_by(MetricaSIGE.anio, MetricaSIGE.mes).all()
        df_sige = pd.DataFrame([{
            "Año": m.anio,
            "Mes": m.mes,
            "Matrícula Oficial": m.matricula_oficial,
            "% Asistencia Validada": m.asistencia_oficial_validada,
            "Calificaciones Consolidadas": m.calificaciones_consolidadas,
            "Observaciones": m.observaciones or "",
        } for m in sige])
        zf.writestr("04_metricas_sige.csv", df_sige.to_csv(index=False).encode("utf-8-sig"))

        # 5. README explicativo
        stats = _estadisticas_globales(acciones)
        readme = f"""PAQUETE DE AUDITORÍA PME - EduGest
====================================
Generado el: {fecha_gen}

Contenido:
1. 01_matriz_rendicion_pme.xlsx  → Consolidado de acciones, presupuesto e indicadores.
2. 02_indicadores_historicos.csv → Evolución mensual de IEA, correlación y semáforos por acción.
3. 03_participaciones_alumnos.csv→ Trazabilidad de participación de estudiantes en cada acción.
4. 04_metricas_sige.csv          → Métricas oficiales consolidadas reportadas al SIGE.

Resumen global:
- Acciones registradas: {len(acciones)}
- Presupuesto asignado: ${stats['total_asignado']:,.0f}
- Presupuesto ejecutado: ${stats['total_ejecutado']:,.0f} ({stats['pje_ejecucion']}%)
- Semáforos: {stats['semaforos']['Verde']} Verde / {stats['semaforos']['Amarillo']} Amarillo / {stats['semaforos']['Rojo']} Rojo
"""
        zf.writestr("README.txt", readme.encode("utf-8"))

    buffer.seek(0)
    nombre = f"Auditoria_PME_{datetime.now().strftime('%Y%m%d')}.zip"
    return send_file(buffer, download_name=nombre, as_attachment=True, mimetype="application/zip")
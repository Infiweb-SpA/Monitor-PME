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
    IndicadorAccion, ParticipacionAccion, MetricaSIGE, Estudiante,
    DefinicionIndicador, MedicionIndicador
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
            # Nuevos campos (modelo nuevo)
            "IPA (%)": indicador.ipa if indicador else None,
            "Progreso Promedio (%)": indicador.progreso_promedio if indicador else None,
            "Delta Promedio": indicador.delta_promedio if indicador else None,
            "% Estudiantes Mejora": indicador.porcentaje_mejora if indicador else None,
            "% Meta Alcanzada": indicador.porcentaje_meta_alcanzada if indicador else None,
            "% Retroceso": indicador.porcentaje_retroceso if indicador else None,
        })
    return pd.DataFrame(data)


def _estadisticas_globales(acciones):
    """Calcula KPIs globales para el reporte ejecutivo y la vista previa."""
    total_asignado = sum(a.presupuesto_asignado for a in acciones)
    total_ejecutado = sum(a.presupuesto_ejecutado for a in acciones)
    pje_ejecucion = (total_ejecutado / total_asignado * 100) if total_asignado > 0 else 0.0

    semaforos = {"Verde": 0, "Amarillo": 0, "Rojo": 0, "Sin Datos": 0}
    ieas, ipas, progresos = [], [], []

    for acc in acciones:
        ind = acc.indicadores.order_by(IndicadorAccion.mes.desc()).first()
        estado = ind.estado_semaforo if ind else "Sin Datos"
        semaforos[estado] = semaforos.get(estado, 0) + 1
        if ind and ind.iea is not None:
            ieas.append(ind.iea)
        if ind and ind.ipa is not None:
            ipas.append(ind.ipa)
        if ind and ind.progreso_promedio is not None:
            progresos.append(ind.progreso_promedio)

    return {
        "total_asignado": total_asignado,
        "total_ejecutado": total_ejecutado,
        "pje_ejecucion": round(pje_ejecucion, 1),
        "semaforos": semaforos,
        "iea_promedio": round(sum(ieas) / len(ieas), 2) if ieas else None,
        "ipa_promedio": round(sum(ipas) / len(ipas), 1) if ipas else None,
        "progreso_promedio": round(sum(progresos) / len(progresos), 1) if progresos else None,
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
        acciones=acciones, dimensiones=dimensiones, cursos=cursos,
        establecimiento=establecimiento, total_acciones=len(acciones), **stats,
    )


@reportes_bp.route("/ejecutivo")
@login_required
def reporte_ejecutivo():
    """Vista HTML imprimible del Reporte Ejecutivo para el Sostenedor."""
    establecimiento = Establecimiento.query.first()
    acciones = AccionPME.query.all()
    stats = _estadisticas_globales(acciones)

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
            "ipa": ind.ipa if ind else None,
            "progreso": ind.progreso_promedio if ind else None,
        })

    alertas = [f for f in filas if f["semaforo"] in ("Rojo", "Amarillo")]

    return render_template(
        "reportes/ejecutivo.html",
        establecimiento=establecimiento, fecha=datetime.now(),
        filas=filas, alertas=alertas, **stats,
    )


# ============================================================
# EXPORTACIONES
# ============================================================

@reportes_bp.route("/exportar_excel")
@login_required
def exportar_excel():
    """Matriz de Rendición en Excel. Acepta filtros del Reporte Personalizado."""
    query = AccionPME.query

    dim_ids = request.args.get("dimensiones")
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
            query = query.filter(AccionPME.fecha_inicio >= datetime.strptime(desde, "%Y-%m-%d").date())
        except ValueError:
            pass

    hasta = request.args.get("hasta")
    if hasta:
        try:
            query = query.filter(AccionPME.fecha_fin <= datetime.strptime(hasta, "%Y-%m-%d").date())
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
    return send_file(output, download_name=nombre, as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@reportes_bp.route("/auditoria")
@login_required
def auditoria_zip():
    """ZIP con trazabilidad completa del PME para auditoría."""
    acciones = AccionPME.query.all()
    if not acciones:
        flash("No hay datos registrados para generar el paquete de auditoría.", "warning")
        return redirect(url_for("reportes.index"))

    buffer = io.BytesIO()
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. Matriz de Rendición
        df_acc = _df_acciones(acciones)
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            df_acc.to_excel(writer, index=False, sheet_name="Matriz Rendición")
        excel_buf.seek(0)
        zf.writestr("01_matriz_rendicion_pme.xlsx", excel_buf.read())

        # 2. Indicadores históricos (actualizado con nuevos campos)
        inds = IndicadorAccion.query.join(AccionPME).order_by(AccionPME.id, IndicadorAccion.mes).all()
        df_ind = pd.DataFrame([{
            "Acción": i.accion.nombre,
            "Código": i.accion.codigo_interno or "",
            "Periodo": i.mes,
            "IEA": i.iea,
            "IPA (%)": i.ipa,
            "Progreso Promedio (%)": i.progreso_promedio,
            "Delta Promedio": i.delta_promedio,
            "% Mejora": i.porcentaje_mejora,
            "% Meta Alcanzada": i.porcentaje_meta_alcanzada,
            "% Retroceso": i.porcentaje_retroceso,
            "Correlación Pearson": i.correlacion_pearson,
            "Proyección Cumplimiento": i.proyeccion_cumplimiento,
            "Semáforo": i.estado_semaforo,
            "Gasto del Mes ($)": i.gasto_mes,
        } for i in inds])
        zf.writestr("02_indicadores_historicos.csv", df_ind.to_csv(index=False).encode("utf-8-sig"))

        # 3. Participaciones de alumnos
        parts = (db.session.query(ParticipacionAccion, Estudiante, AccionPME)
                 .join(Estudiante, ParticipacionAccion.estudiante_id == Estudiante.id)
                 .join(AccionPME, ParticipacionAccion.accion_id == AccionPME.id).all())
        df_part = pd.DataFrame([{
            "Estudiante": e.nombre_completo, "Matrícula": e.matricula,
            "Curso": e.curso.nombre if e.curso else "",
            "Acción PME": a.nombre, "Código Acción": a.codigo_interno or "",
            "Horas Asistencia": p.horas_asistencia,
            "Talleres Asistidos": p.asistencia_talleres,
            "Fecha Registro": p.fecha_registro.strftime("%d/%m/%Y") if p.fecha_registro else "",
        } for p, e, a in parts])
        zf.writestr("03_participaciones_alumnos.csv", df_part.to_csv(index=False).encode("utf-8-sig"))

        # 4. Métricas SIGE
        sige = MetricaSIGE.query.order_by(MetricaSIGE.anio, MetricaSIGE.mes).all()
        df_sige = pd.DataFrame([{
            "Año": m.anio, "Mes": m.mes,
            "Matrícula Oficial": m.matricula_oficial,
            "% Asistencia Validada": m.asistencia_oficial_validada,
            "Calificaciones Consolidadas": m.calificaciones_consolidadas,
            "Observaciones": m.observaciones or "",
        } for m in sige])
        zf.writestr("04_metricas_sige.csv", df_sige.to_csv(index=False).encode("utf-8-sig"))

        # 5. Mediciones de indicadores (nuevo)
        meds = (db.session.query(MedicionIndicador, DefinicionIndicador, Estudiante)
                .join(DefinicionIndicador, MedicionIndicador.indicador_def_id == DefinicionIndicador.id)
                .join(Estudiante, MedicionIndicador.estudiante_id == Estudiante.id)
                .order_by(DefinicionIndicador.accion_id, MedicionIndicador.periodo).all())
        df_meds = pd.DataFrame([{
            "Estudiante": e.nombre_completo, "Matrícula": e.matricula,
            "Indicador": d.nombre, "Tipo": d.tipo, "Dirección": d.direccion,
            "Unidad": d.unidad_medida or "", "Línea Base": d.linea_base, "Meta": d.meta,
            "Periodo": m.periodo, "Valor": m.valor, "Observación": m.observacion or "",
        } for m, d, e in meds])
        zf.writestr("05_mediciones_indicadores.csv", df_meds.to_csv(index=False).encode("utf-8-sig"))

        # 6. README
        stats = _estadisticas_globales(acciones)
        ipa_line = f"- IPA promedio: {stats['ipa_promedio']}%\n" if stats['ipa_promedio'] else ""
        readme = f"""PAQUETE DE AUDITORÍA PME - EduGest
====================================
Generado el: {fecha_gen}

Contenido:
1. 01_matriz_rendicion_pme.xlsx  → Consolidado de acciones, presupuesto e indicadores.
2. 02_indicadores_historicos.csv → Evolución mensual de IEA, IPA, progreso y semáforos.
3. 03_participaciones_alumnos.csv→ Trazabilidad de participación de estudiantes.
4. 04_metricas_sige.csv          → Métricas oficiales consolidadas (SIGE).
5. 05_mediciones_indicadores.csv → Mediciones de indicadores pedagógicos por estudiante.

Resumen global:
- Acciones registradas: {len(acciones)}
- Presupuesto asignado: ${stats['total_asignado']:,.0f}
- Presupuesto ejecutado: ${stats['total_ejecutado']:,.0f} ({stats['pje_ejecucion']}%)
- IEA promedio: {stats['iea_promedio'] or 'N/A'}
{ipa_line}- Semáforos: {stats['semaforos']['Verde']} Verde / {stats['semaforos']['Amarillo']} Amarillo / {stats['semaforos']['Rojo']} Rojo
"""
        zf.writestr("README.txt", readme.encode("utf-8"))

    buffer.seek(0)
    nombre = f"Auditoria_PME_{datetime.now().strftime('%Y%m%d')}.zip"
    return send_file(buffer, download_name=nombre, as_attachment=True, mimetype="application/zip")
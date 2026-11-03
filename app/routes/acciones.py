"""Blueprint de acciones PME."""
import io
import json
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_required
import pandas as pd
from app.extensions import db
from app.models.pme import AccionPME, ObjetivoPME, DimensionPME
from app.models.metrics import IndicadorAccion, DefinicionIndicador, ParticipacionAccion
from app.services.pme_engine import (obtener_impacto_individual, obtener_impacto_individual_nuevo,
                                     procesar_indicadores_accion, desglosar_periodo)
from app.utils import parse_date


acciones_bp = Blueprint("acciones", __name__, template_folder="../templates/acciones")

# Estados validos de una accion PME (ver AccionPME.estado en models/pme.py)
ESTADOS_ACCION = ("Planificada", "En Ejecución", "Finalizada", "Cancelada")

# Etiquetas y colores de la gráfica de distribución de alumnos
_DISTRIB_NUEVO = {
    "META_ALCANZADA": ("Meta alcanzada", "#22c55e"),
    "EN_PROGRESO": ("En progreso", "#06b6d4"),
    "ESTABLE": ("Sin cambio", "#9ca3af"),
    "RETROCESO": ("Retroceso", "#ef4444"),
    "SIN_DATOS": ("Sin datos", "#e5e7eb"),
}
_DISTRIB_LEGACY = {
    "Mejora alta": ("Mejora alta", "#22c55e"),
    "Mejora leve": ("Mejora leve", "#06b6d4"),
    "Estable": ("Estable", "#9ca3af"),
    "Retroceso": ("Retroceso", "#ef4444"),
    "Sin datos": ("Sin datos", "#e5e7eb"),
}


@acciones_bp.route("/")
@login_required
def index():
    """Listado general de acciones PME."""
    acciones = AccionPME.query.order_by(AccionPME.created_at.desc()).all()
    return render_template("acciones/index.html", acciones=acciones)


@acciones_bp.route("/detalle/<int:accion_id>")
@login_required
def detalle(accion_id):
    """Vista de detalle y analítica de impacto de una acción específica."""
    accion = AccionPME.query.get_or_404(accion_id)
    indicador = accion.indicadores.order_by(IndicadorAccion.mes.desc()).first()
    historico = accion.indicadores.order_by(IndicadorAccion.mes.asc()).all()

    # Detectar si la acción usa modelo nuevo o legacy
    definiciones = DefinicionIndicador.query.filter_by(
        accion_id=accion_id, activo=True
    ).all()

    if definiciones:
        alumnos = obtener_impacto_individual_nuevo(accion_id)
        mapa_distrib = _DISTRIB_NUEVO
        clave = lambda a: a.get("estado_grupal")
    else:
        alumnos = obtener_impacto_individual(accion_id)
        mapa_distrib = _DISTRIB_LEGACY
        clave = lambda a: a.get("clasificacion")

    # Distribución de alumnos por estado (para la gráfica doughnut)
    conteos = {}
    for a in alumnos:
        k = clave(a)
        if k in mapa_distrib:
            conteos[k] = conteos.get(k, 0) + 1
    distribucion = [
        {"label": mapa_distrib[k][0], "valor": conteos[k], "color": mapa_distrib[k][1]}
        for k in mapa_distrib if conteos.get(k)
    ]

    # Semestres con horas registradas: origen del reparto en la gráfica
    periodos_semestre = sorted({
        p[0] for p in db.session.query(ParticipacionAccion.periodo)
        .filter(ParticipacionAccion.accion_id == accion_id,
                ParticipacionAccion.periodo.like("%-S%"))
        .distinct().all() if p[0]
    })

    return render_template(
        "acciones/detalle.html",
        accion=accion, indicador=indicador,
        historico=historico, alumnos=alumnos,
        definiciones=definiciones,
        estados_accion=ESTADOS_ACCION,
        distribucion=distribucion,
        periodos_semestre=periodos_semestre,
    )


@acciones_bp.route("/recalcular/<int:accion_id>", methods=["POST"])
@login_required
def recalcular(accion_id):
    """Vuelve a correr el motor para todos los periodos con horas registradas.

    Permite desglosar en meses un semestre ya cargado (reparto equitativo de
    horas) sin tener que volver a registrar las participaciones.
    """
    accion = AccionPME.query.get_or_404(accion_id)
    periodos = [p[0] for p in db.session.query(ParticipacionAccion.periodo)
                .filter(ParticipacionAccion.accion_id == accion_id).distinct().all() if p[0]]
    if not periodos:
        flash("Esta acción no tiene horas registradas para recalcular (cargue datos con F-4).", "warning")
        return redirect(url_for("acciones.detalle", accion_id=accion_id))

    # Meses primero y semestres al final: el desglose del semestre sobrescribe
    # con su reparto equitativo los meses que ya estaban calculados.
    periodos.sort(key=lambda p: (len(desglosar_periodo(p)) > 1, p))

    procesados, sin_datos = [], []
    for per in periodos:
        ind = procesar_indicadores_accion(accion_id, per)
        (procesados if ind else sin_datos).append(per)

    if procesados:
        msg = f"Indicadores recalculados para: {', '.join(procesados)}."
        if sin_datos:
            msg += f" Sin datos para: {', '.join(sin_datos)}."
        flash(msg, "success")
    else:
        flash("No se pudieron recalcular los indicadores: faltan notas o mediciones.", "warning")

    return redirect(url_for("acciones.detalle", accion_id=accion_id))


@acciones_bp.route("/cambiar_estado/<int:accion_id>", methods=["POST"])
@login_required
def cambiar_estado(accion_id):
    """Cambia el estado de una acción (usado desde la vista de detalle)."""
    accion = AccionPME.query.get_or_404(accion_id)
    nuevo = (request.form.get("estado") or "").strip()

    if nuevo not in ESTADOS_ACCION:
        flash(f"Estado no válido: «{nuevo}». Use uno de: {', '.join(ESTADOS_ACCION)}.", "error")
    elif nuevo == accion.estado:
        flash(f"La acción ya está en estado «{nuevo}».", "info")
    else:
        anterior = accion.estado
        accion.estado = nuevo
        db.session.commit()
        flash(f"Estado de «{accion.nombre}» actualizado: {anterior} → {nuevo}.", "success")

    return redirect(url_for("acciones.detalle", accion_id=accion_id))


@acciones_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva_accion():
    if request.method == "POST":
        objetivo_id = request.form.get("objetivo_id")
        nombre = request.form.get("nombre")
        if not nombre or not objetivo_id:
            flash("El nombre y el objetivo son obligatorios", "error")
            return redirect(url_for("acciones.nueva_accion"))

        count = AccionPME.query.count()
        codigo = f"ACC-2026-{count + 1:03d}"
        f_inicio = parse_date(request.form.get("fecha_inicio"))
        f_fin = parse_date(request.form.get("fecha_fin"))

        nueva = AccionPME(
            objetivo_id=int(objetivo_id),
            nombre=nombre,
            descripcion=request.form.get("descripcion", ""),
            presupuesto_asignado=float(request.form.get("presupuesto_asignado", 0.0)),
            presupuesto_ejecutado=float(request.form.get("presupuesto_ejecutado", 0.0)),
            fuente_financiamiento=request.form.get("fuente_financiamiento"),
            codigo_interno=codigo,
            estado=request.form.get("estado", "Planificada"),
            responsable=request.form.get("responsable"),
            fecha_inicio=f_inicio,
            fecha_fin=f_fin,
            meta_cualitativa=request.form.get("meta_cualitativa", ""),
            meta_cuantitativa=request.form.get("meta_cuantitativa", ""),
            indicador_tipo=request.form.get("indicador_tipo"),
            unidad_medida=request.form.get("unidad_medida"),
            linea_base_valor=float(request.form.get("linea_base_valor")) if request.form.get("linea_base_valor") else None,
            meta_valor=float(request.form.get("meta_valor")) if request.form.get("meta_valor") else None,
            curso_objetivo=request.form.get("curso_objetivo"),
            curso_control=request.form.get("curso_control")
        )
        db.session.add(nueva)
        db.session.commit()

        # Convertir campos basicos en un indicador automatico (modelo unificado)
        tipo_basico = request.form.get("indicador_tipo")
        linea_base_basica = request.form.get("linea_base_valor")
        meta_basica = request.form.get("meta_valor")
        if tipo_basico and linea_base_basica and meta_basica:
            try:
                tipo_ind = "NOTA" if tipo_basico == "Promedio Notas" else "ASISTENCIA"
                def_basica = DefinicionIndicador(
                    accion_id=nueva.id,
                    nombre=tipo_basico,
                    descripcion="Indicador basico generado automaticamente desde F-1",
                    tipo=tipo_ind,
                    unidad_medida=request.form.get("unidad_medida", ""),
                    direccion="MAYOR_ES_MEJOR",
                    linea_base=float(linea_base_basica),
                    meta=float(meta_basica),
                    peso=1.0,
                )
                db.session.add(def_basica)
                db.session.commit()
            except (ValueError, TypeError):
                pass


        # Procesar indicadores de evaluación (modelo nuevo)
        nombres_ind = request.form.getlist('ind_nombre[]')
        tipos_ind = request.form.getlist('ind_tipo[]')
        unidades_ind = request.form.getlist('ind_unidad[]')
        asignaturas_ind = request.form.getlist('ind_asignatura[]')
        direcciones_ind = request.form.getlist('ind_direccion[]')
        bases_ind = request.form.getlist('ind_linea_base[]')
        metas_ind = request.form.getlist('ind_meta[]')
        pesos_ind = request.form.getlist('ind_peso[]')
        descs_ind = request.form.getlist('ind_descripcion[]')
        metodos_ind = request.form.getlist('ind_metodo[]')
        frecs_ind = request.form.getlist('ind_frecuencia[]')

        indicadores_creados = 0
        for i, nombre_ind in enumerate(nombres_ind):
            nombre_ind = nombre_ind.strip()
            if not nombre_ind:
                continue
            try:
                def_ind = DefinicionIndicador(
                    accion_id=nueva.id,
                    nombre=nombre_ind,
                    descripcion=descs_ind[i].strip() if i < len(descs_ind) else '',
                    tipo=tipos_ind[i] if i < len(tipos_ind) else 'OTRO_CUANTITATIVO',
                    unidad_medida=unidades_ind[i].strip() if i < len(unidades_ind) else '',
                    asignatura=asignaturas_ind[i].strip() if i < len(asignaturas_ind) and asignaturas_ind[i].strip() else None,
                    direccion=direcciones_ind[i] if i < len(direcciones_ind) else 'MAYOR_ES_MEJOR',
                    linea_base=float(bases_ind[i]) if i < len(bases_ind) and bases_ind[i].strip() else None,
                    meta=float(metas_ind[i]) if i < len(metas_ind) and metas_ind[i].strip() else None,
                    peso=float(pesos_ind[i]) if i < len(pesos_ind) and pesos_ind[i].strip() else 1.0,
                    metodo_evaluacion=metodos_ind[i].strip() if i < len(metodos_ind) and metodos_ind[i].strip() else None,
                    frecuencia_medicion=frecs_ind[i].strip() if i < len(frecs_ind) and frecs_ind[i].strip() else None,
                )
                db.session.add(def_ind)
                indicadores_creados += 1
            except (ValueError, IndexError) as e:
                flash(f"Error en indicador '{nombre_ind}': {str(e)}", "warning")

        if indicadores_creados > 0:
            db.session.commit()
            flash(f"{indicadores_creados} indicador(es) definido(s) para la acción.", "success")

        flash(f"Acción PME creada exitosamente. Código: {codigo}", "success")
        return redirect(url_for("ingesta.index"))

    objetivos = ObjetivoPME.query.filter_by(estado="Activo").all()
    return render_template("acciones/nueva.html", objetivos=objetivos)


# --- LÓGICA DE EXCEL ---

@acciones_bp.route("/plantilla_excel")
@login_required
def descargar_plantilla():
    """Genera y descarga un archivo Excel plantilla formateado."""
    data = {
        "Nombre Acción": ["Taller de Refuerzo Matemático"],
        "Descripción": ["Refuerzo de algebra para alumnos de 8vo"],
        "Objetivo ID": [1],
        "Presupuesto Asignado": [2500000],
        "Fuente Financiamiento": ["SEP"],
        "Responsable": ["Prof. Marta Díaz"],
        "Fecha Inicio (AAAA-MM-DD)": ["2026-03-01"],
        "Fecha Fin (AAAA-MM-DD)": ["2026-11-30"],
        "Estado": ["En Ejecución"],
        "Indicador Tipo": ["Promedio Notas"],
        "Unidad de Medida": ["Promedio Calificaciones (1.0-7.0)"],
        "Linea Base Valor": [4.5],
        "Meta Valor": [5.5],
        "Meta Cuantitativa": ["+0.8 pts promedio matemáticas"],
        "Curso Objetivo": ["8° Básico"]
    }
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla PME')
    output.seek(0)
    return send_file(output, download_name='plantilla_acciones_pme.xlsx', as_attachment=True)


@acciones_bp.route("/guardar_excel", methods=["POST"])
@login_required
def guardar_excel():
    """Guarda en la BD los datos previsualizados desde la sesión."""
    datos_str = session.get('preview_data')
    if not datos_str:
        flash("No hay datos en la vista previa para guardar.", "error")
        return redirect(url_for("ingesta.index"))
    datos = json.loads(datos_str)
    count = AccionPME.query.count()
    agregadas = 0
    for row in datos:
        try:
            count += 1
            codigo = f"ACC-2026-{count:03d}"
            acc = AccionPME(
                objetivo_id=int(row.get("Objetivo ID", 1)),
                nombre=row.get("Nombre Acción"),
                descripcion=row.get("Descripción"),
                presupuesto_asignado=float(row.get("Presupuesto Asignado", 0) or 0),
                fuente_financiamiento=row.get("Fuente Financiamiento"),
                codigo_interno=codigo,
                estado=row.get("Estado", "Planificada"),
                responsable=row.get("Responsable"),
                fecha_inicio=parse_date(row.get("Fecha Inicio (AAAA-MM-DD)")),
                fecha_fin=parse_date(row.get("Fecha Fin (AAAA-MM-DD)")),
                indicador_tipo=row.get("Indicador Tipo"),
                unidad_medida=row.get("Unidad de Medida"),
                linea_base_valor=float(row.get("Linea Base Valor") or 0),
                meta_valor=float(row.get("Meta Valor") or 0),
                meta_cuantitativa=row.get("Meta Cuantitativa"),
                curso_objetivo=row.get("Curso Objetivo")
            )
            db.session.add(acc)
            agregadas += 1
        except Exception as e:
            flash(f"Error en fila {count}: {str(e)}", "error")
    db.session.commit()
    session.pop('preview_data', None)
    flash(f"¡Éxito! {agregadas} acciones importadas desde Excel.", "success")
    return redirect(url_for("ingesta.index"))


@acciones_bp.route("/cargar_excel", methods=["POST"])
@login_required
def cargar_excel():
    """Lee el Excel subido y lo guarda en sesión para previsualizar."""
    file = request.files.get('file_excel')
    if not file:
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for("ingesta.index"))
    try:
        df = pd.read_excel(file)
        if 'Nombre Acción' not in df.columns or 'Objetivo ID' not in df.columns:
            flash("El Excel no tiene las columnas requeridas.", "error")
            return redirect(url_for("ingesta.index"))
        df = df.where(pd.notnull(df), None)
        datos = df.to_dict(orient='records')
        session['preview_data'] = json.dumps(datos, default=str)
        flash("Archivo leído. Revise la vista previa antes de guardar.", "info")
        return redirect(url_for("ingesta.index"))
    except Exception as e:
        flash(f"Error al leer el Excel: {str(e)}", "error")
        return redirect(url_for("ingesta.index"))


@acciones_bp.route("/cancelar_excel")
@login_required
def cancelar_excel():
    session.pop('preview_data', None)
    flash("Carga de Excel cancelada.", "info")
    return redirect(url_for("ingesta.index"))
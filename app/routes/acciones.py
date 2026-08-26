"""Blueprint de acciones PME."""
import io
import json
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_required
import pandas as pd
from app.extensions import db
from app.models.pme import AccionPME, ObjetivoPME, DimensionPME
from app.models.metrics import IndicadorAccion
from app.services.pme_engine import obtener_impacto_individual


acciones_bp = Blueprint("acciones", __name__, template_folder="../templates/acciones")


def parse_date(fecha_str):
    """Convierte un string 'YYYY-MM-DD' a un objeto date de Python."""
    if not fecha_str or pd.isna(fecha_str):
        return None
    try:
        # Si viene de Pandas (Timestamp)
        if isinstance(fecha_str, pd.Timestamp):
            return fecha_str.date()
        # Si viene de un formulario HTML (String)
        if isinstance(fecha_str, str):
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
        # Si ya es un date
        if isinstance(fecha_str, date):
            return fecha_str
    except Exception:
        return None
    return None


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
    
    # NUEVO: Impacto individual por alumno
    alumnos = obtener_impacto_individual(accion_id)
    
    return render_template(
        "acciones/detalle.html",
        accion=accion,
        indicador=indicador,
        historico=historico,
        alumnos=alumnos  # NUEVO
    )

@acciones_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva_accion():
    if request.method == "POST":
        objetivo_id = request.form.get("objetivo_id")
        nombre = request.form.get("nombre")
        
        if not nombre or not objetivo_id:
            flash("El nombre y el objetivo son obligatorios", "error")
            return redirect(url_for("acciones.nueva_accion"))

        # Generar Código Interno Automático
        count = AccionPME.query.count()
        codigo = f"ACC-2026-{count + 1:03d}"

        # Convertir fechas de string a objeto date
        f_inicio = parse_date(request.form.get("fecha_inicio"))
        f_fin = parse_date(request.form.get("fecha_fin"))

        nueva = AccionPME(
            objetivo_id=int(objetivo_id),
            nombre=nombre,
            descripcion=request.form.get("descripcion", ""),
            presupuesto_asignado=float(request.form.get("presupuesto_asignado", 0.0)),
            presupuesto_ejecutado=float(request.form.get("presupuesto_ejecutado", 0.0)), # AGREGAR ESTA LÍNEA
            fuente_financiamiento=request.form.get("fuente_financiamiento"),
            codigo_interno=codigo,
            estado=request.form.get("estado", "Planificada"),
            responsable=request.form.get("responsable"),
            fecha_inicio=f_inicio,
            fecha_fin=f_fin,
            meta_cualitativa=request.form.get("meta_cualitativa", ""),
            # AQUÍ ESTABA FALTANDO ESTA LÍNEA:
            meta_cuantitativa=request.form.get("meta_cuantitativa", ""),
            indicador_tipo=request.form.get("indicador_tipo"),
            unidad_medida=request.form.get("unidad_medida"),
            linea_base_valor=float(request.form.get("linea_base_valor")) if request.form.get("linea_base_valor") else None,
            meta_valor=float(request.form.get("meta_valor")) if request.form.get("meta_valor") else None,
            curso_objetivo=request.form.get("curso_objetivo")
        )
        
        db.session.add(nueva)
        db.session.commit()
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
                descripcion=row.get("Descripción"), # NUEVO
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
                meta_cuantitativa=row.get("Meta Cuantitativa"), # NUEVO
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
        # Validar columnas mínimas
        if 'Nombre Acción' not in df.columns or 'Objetivo ID' not in df.columns:
            flash("El Excel no tiene las columnas requeridas (Nombre Acción, Objetivo ID).", "error")
            return redirect(url_for("ingesta.index"))
        
        # Reemplazar NaN por None para que sea compatible con la BD
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
"""Blueprint de ingesta de datos."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.pme import AccionPME, DimensionPME, ObjetivoPME
from app.models.metrics import RegistroAppPonderado, MetricaSIGE, ParticipacionAccion, Estudiante
from app.services.pme_engine import procesar_indicadores_accion

ingesta_bp = Blueprint("ingesta", __name__, template_folder="../templates/ingesta")


@ingesta_bp.route("/")
@login_required
def index():
    """Panel principal de ingesta de datos."""
    # Pasamos acciones, dimensiones y estudiantes a la vista
    acciones = AccionPME.query.filter(AccionPME.estado.in_(["Planificada", "En Ejecución"])).all()
    dimensiones = DimensionPME.query.all()
    estudiantes = Estudiante.query.filter_by(activo=True).all()
    
    return render_template("ingesta/index.html", acciones=acciones, dimensiones=dimensiones, estudiantes=estudiantes)


@ingesta_bp.route("/app_ponderado", methods=["POST"])
@login_required
def cargar_app_ponderado():
    """Carga individual de datos de App Ponderado (F-2) con justificación."""
    estudiante_id = request.form.get("estudiante_id")
    periodo = request.form.get("periodo")
    asignatura = request.form.get("asignatura")
    promedio = request.form.get("promedio_notas")
    asistencia = request.form.get("porcentaje_asistencia")
    bitacora = request.form.get("bitacora") # Justificación de la intervención

    if not all([estudiante_id, periodo, asignatura, promedio, asistencia]):
        flash("Todos los campos de App Ponderado son obligatorios", "error")
        return redirect(url_for("ingesta.index"))

    registro = RegistroAppPonderado(
        estudiante_id=int(estudiante_id),
        periodo=periodo,
        asignatura=asignatura,
        promedio_notas=float(promedio),
        porcentaje_asistencia=float(asistencia),
        bitacora=bitacora
    )
    db.session.add(registro)
    db.session.commit()

    flash("Registro de App Ponderado guardado y bitácora actualizada.", "success")
    return redirect(url_for("ingesta.index"))


@ingesta_bp.route("/sige", methods=["POST"])
@login_required
def cargar_sige():
    """Carga de métricas oficiales SIGE (F-3) con justificación."""
    establecimiento_id = 1 
    anio = request.form.get("anio")
    mes = request.form.get("mes")
    matricula = request.form.get("matricula_oficial")
    asistencia_validada = request.form.get("asistencia_oficial_validada")
    observaciones = request.form.get("observaciones") # Justificación de gasto/desviación

    if not all([anio, mes, matricula, asistencia_validada]):
        flash("Todos los campos SIGE son obligatorios", "error")
        return redirect(url_for("ingesta.index"))

    metrica = MetricaSIGE(
        establecimiento_id=establecimiento_id,
        anio=int(anio),
        mes=int(mes),
        matricula_oficial=int(matricula),
        asistencia_oficial_validada=float(asistencia_validada),
        observaciones=observaciones
    )
    db.session.add(metrica)
    db.session.commit()

    flash("Métricas SIGE guardadas correctamente.", "success")
    return redirect(url_for("ingesta.index"))


@ingesta_bp.route("/participacion", methods=["POST"])
@login_required
def cargar_participacion():
    """Carga de múltiples estudiantes en una acción PME (F-4) y disparo del motor."""
    estudiante_ids = request.form.getlist("estudiantes[]") # ARRAY DE ALUMNOS
    accion_id = request.form.get("accion_id")
    horas = request.form.get("horas_asistencia", 0.0)
    periodo = request.form.get("periodo")

    if not estudiante_ids or not accion_id or not periodo:
        flash("Debe seleccionar al menos un estudiante, una acción y un período", "error")
        return redirect(url_for("ingesta.index"))

    # Loop para insertar a todos los seleccionados
    for est_id in estudiante_ids:
        participacion = ParticipacionAccion(
            estudiante_id=int(est_id),
            accion_id=int(accion_id),
            horas_asistencia=float(horas)
        )
        db.session.add(participacion)
    
    db.session.commit()

    # --- LA MAGIA DEL MOTOR ---
    indicador = procesar_indicadores_accion(int(accion_id), periodo)
    
    if indicador:
        flash(f"Motor actualizado. {len(estudiante_ids)} alumnos cargados. Semáforo: {indicador.estado_semaforo}", "info")
    else:
        flash("Participación guardada. Faltan datos en App Ponderado para calcular indicadores.", "warning")

    return redirect(url_for("ingesta.index"))
"""Blueprint de ingesta de datos."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.pme import AccionPME, DimensionPME, ObjetivoPME
from app.models.metrics import (RegistroAppPonderado, MetricaSIGE, ParticipacionAccion,
                                 Estudiante, DefinicionIndicador, MedicionIndicador)
from app.services.pme_engine import procesar_indicadores_accion, desglosar_periodo

ingesta_bp = Blueprint("ingesta", __name__, template_folder="../templates/ingesta")

# Año de gestión y rangos fijos de semestre (formato periodo "YYYY-MM")
ANIO_GESTION = 2026
SEMESTRES = {
    "2026-S1": ("2026-03", "2026-06"),
    "2026-S2": ("2026-07", "2026-10"),
}
ETIQUETAS_SEMESTRE = {
    "2026-S1": "Promedio semestre 1 (2026-03 a 2026-06)",
    "2026-S2": "Promedio semestre 2 (2026-07 a 2026-10)",
}


@ingesta_bp.route("/")
@login_required
def index():
    """Panel principal de ingesta de datos."""
    acciones = AccionPME.query.filter(AccionPME.estado.in_(["Planificada", "En Ejecución"])).all()
    dimensiones = DimensionPME.query.all()
    estudiantes = Estudiante.query.filter_by(activo=True).all()
    # Asignaturas distintas ya registradas (para asociar competencias)
    asignaturas = [r[0] for r in db.session.query(RegistroAppPonderado.asignatura).distinct().all()]
    # Periodos disponibles en F-4: meses del año de gestión (marzo a octubre)
    meses_gestion = [f"{ANIO_GESTION}-{m:02d}" for m in range(3, 11)]
    return render_template("ingesta/index.html", acciones=acciones,
                           dimensiones=dimensiones, estudiantes=estudiantes,
                           asignaturas=asignaturas,
                           meses_gestion=meses_gestion,
                           semestres=SEMESTRES, etiquetas_semestre=ETIQUETAS_SEMESTRE)


# --- NUEVO: Endpoint AJAX para indicadores de una acción ---
@ingesta_bp.route("/indicadores_de_accion/<int:accion_id>")
@login_required
def indicadores_de_accion(accion_id):
    """Retorna los indicadores activos definidos para una acción (JSON)."""
    defs = DefinicionIndicador.query.filter_by(accion_id=accion_id, activo=True).all()
    resultado = []
    for d in defs:
        resultado.append({
            "id": d.id,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "unidad_medida": d.unidad_medida or "",
            "direccion": d.direccion,
            "linea_base": d.linea_base,
            "meta": d.meta,
            "asignatura": d.asignatura or "Transversal",
        })
    return jsonify(resultado)


# --- NUEVO: Guardar mediciones de indicadores ---
@ingesta_bp.route("/medicion_indicador", methods=["POST"])
@login_required
def cargar_medicion_indicador():
    """Carga mediciones de indicadores para un estudiante en un periodo."""
    estudiante_id = request.form.get("estudiante_id")
    periodo = request.form.get("periodo")
    accion_id = request.form.get("accion_id")

    if not all([estudiante_id, periodo, accion_id]):
        flash("Acción, estudiante y periodo son obligatorios", "error")
        return redirect(url_for("ingesta.index"))

    indicador_ids = request.form.getlist("med_indicador_id[]")
    valores = request.form.getlist("med_valor[]")
    observaciones = request.form.getlist("med_observacion[]")

    if not indicador_ids:
        flash("No se encontraron indicadores. Defina indicadores en F-1 primero.", "warning")
        return redirect(url_for("ingesta.index"))

    guardados = 0
    for i, ind_id in enumerate(indicador_ids):
        valor_str = valores[i].strip() if i < len(valores) else ""
        if not valor_str:
            continue
        try:
            valor = float(valor_str)
        except ValueError:
            continue
        obs = observaciones[i].strip() if i < len(observaciones) else ""
        medicion = MedicionIndicador(
            indicador_def_id=int(ind_id),
            estudiante_id=int(estudiante_id),
            periodo=periodo,
            valor=valor,
            observacion=obs if obs else None,
        )
        db.session.add(medicion)
        guardados += 1

    if guardados > 0:
        db.session.commit()
        flash(f"{guardados} medición(es) registrada(s) para periodo {periodo}. "
              f"Use F-4 para registrar participación y disparar el motor.", "success")
    else:
        flash("No se registraron mediciones (complete al menos un valor).", "warning")

    return redirect(url_for("ingesta.index"))


# --- Rutas existentes (sin cambios) ---

@ingesta_bp.route("/periodos_estudiante")
@login_required
def periodos_estudiante():
    """Devuelve los periodos disponibles para un estudiante en una asignatura (JSON)."""
    estudiante_id = request.args.get("estudiante_id")
    asignatura = request.args.get("asignatura")
    if not all([estudiante_id, asignatura]):
        return jsonify({"periodos": []})
    try:
        eid = int(estudiante_id)
    except (TypeError, ValueError):
        return jsonify({"error": "estudiante_id inválido"}), 400
    regs = RegistroAppPonderado.query.filter_by(
        estudiante_id=eid,
        asignatura=asignatura,
    ).all()
    periodos = sorted({r.periodo for r in regs})
    return jsonify({"periodos": periodos})


@ingesta_bp.route("/notas_estudiante")
@login_required
def notas_estudiante():
    """Devuelve notas/asistencia existentes para un estudiante/periodo/asignatura (JSON)."""
    estudiante_id = request.args.get("estudiante_id")
    periodo = request.args.get("periodo")
    asignatura = request.args.get("asignatura")
    if not all([estudiante_id, periodo, asignatura]):
        return jsonify({"existe": False})
    try:
        eid = int(estudiante_id)
    except (TypeError, ValueError):
        return jsonify({"error": "estudiante_id inválido"}), 400
    reg = RegistroAppPonderado.query.filter_by(
        estudiante_id=eid,
        periodo=periodo,
        asignatura=asignatura,
    ).order_by(
        RegistroAppPonderado.fecha_registro.desc(),
        RegistroAppPonderado.id.desc(),
    ).first()
    if not reg:
        return jsonify({"existe": False})
    return jsonify({
        "existe": True,
        "promedio_notas": reg.promedio_notas,
        "porcentaje_asistencia": reg.porcentaje_asistencia,
    })


def _meses_entre(desde, hasta):
    """Lista los periodos "YYYY-MM" inclusivos entre dos limites."""
    try:
        y1, m1 = int(desde[:4]), int(desde[5:7])
        y2, m2 = int(hasta[:4]), int(hasta[5:7])
    except (ValueError, IndexError, TypeError):
        return []
    meses = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        meses.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
        if len(meses) > 120:  # corte de seguridad
            break
    return meses


@ingesta_bp.route("/notas_periodos")
@login_required
def notas_periodos():
    """Notas/asistencia de un estudiante en una asignatura, opcionalmente en un rango.

    Sin `desde`/`hasta` devuelve todos los periodos con registro.
    Con rango devuelve el promedio simple de los meses que SÍ tienen datos
    (los meses sin registro se excluyen, no se cuentan como 0), mas el
    desglose minimo/maximo y los meses faltantes del rango.
    """
    estudiante_id = request.args.get("estudiante_id")
    asignatura = request.args.get("asignatura")
    desde = (request.args.get("desde") or "").strip()
    hasta = (request.args.get("hasta") or "").strip()

    if not estudiante_id or not asignatura:
        return jsonify({"existe": False, "periodos": [], "registros": []})
    try:
        eid = int(estudiante_id)
    except (TypeError, ValueError):
        return jsonify({"error": "estudiante_id inválido"}), 400

    query = RegistroAppPonderado.query.filter_by(
        estudiante_id=eid, asignatura=asignatura
    )
    if desde:
        query = query.filter(RegistroAppPonderado.periodo >= desde)
    if hasta:
        query = query.filter(RegistroAppPonderado.periodo <= hasta)

    # Orden por periodo ascendente y, dentro del mismo periodo, el registro
    # mas reciente primero: si hay duplicados se usa la fila mas nueva.
    # El desempate por id garantiza determinismo cuando fecha_registro coincide.
    regs = query.order_by(
        RegistroAppPonderado.periodo.asc(),
        RegistroAppPonderado.fecha_registro.desc(),
        RegistroAppPonderado.id.desc(),
    ).all()

    vistos = set()
    registros = []
    for r in regs:
        if r.periodo in vistos:
            continue
        vistos.add(r.periodo)
        registros.append({
            "periodo": r.periodo,
            "promedio_notas": r.promedio_notas,
            "porcentaje_asistencia": r.porcentaje_asistencia,
        })

    meses_rango = _meses_entre(desde, hasta) if (desde and hasta) else []
    faltantes = [m for m in meses_rango if m not in vistos]

    if not registros:
        return jsonify({
            "existe": False,
            "periodos": [],
            "registros": [],
            "n_periodos": 0,
            "n_periodos_rango": len(meses_rango),
            "periodos_faltantes": faltantes,
            "desde": desde or None,
            "hasta": hasta or None,
        })

    notas = [r["promedio_notas"] for r in registros]
    asist = [r["porcentaje_asistencia"] for r in registros]

    return jsonify({
        "existe": True,
        "periodos": [r["periodo"] for r in registros],
        "registros": registros,
        "promedio_notas": round(sum(notas) / len(notas), 2),
        "porcentaje_asistencia": round(sum(asist) / len(asist), 1),
        "nota_min": round(min(notas), 2),
        "nota_max": round(max(notas), 2),
        "asist_min": round(min(asist), 1),
        "asist_max": round(max(asist), 1),
        "n_periodos": len(registros),
        "n_periodos_rango": len(meses_rango) if meses_rango else None,
        "periodos_faltantes": faltantes,
        "desde": desde or None,
        "hasta": hasta or None,
    })


@ingesta_bp.route("/app_ponderado", methods=["POST"])
@login_required
def cargar_app_ponderado():
    """Carga individual de datos de App Ponderado (F-2) con justificación."""
    estudiante_id = request.form.get("estudiante_id")
    periodo = request.form.get("periodo")
    asignatura = request.form.get("asignatura")
    promedio = request.form.get("promedio_notas")
    asistencia = request.form.get("porcentaje_asistencia")
    bitacora = request.form.get("bitacora")
    grupo = request.form.get("grupo", "Intervenido")
    competencia = request.form.get("competencia", "").strip()

    if not all([estudiante_id, periodo, asignatura, promedio, asistencia]):
        flash("Todos los campos de App Ponderado son obligatorios", "error")
        return redirect(url_for("ingesta.index"))

    if competencia:
        bitacora = (bitacora or "") + f"\n[Competencia: {competencia}]"

    registro = RegistroAppPonderado(
        estudiante_id=int(estudiante_id),
        periodo=periodo,
        asignatura=asignatura,
        promedio_notas=float(promedio),
        porcentaje_asistencia=float(asistencia),
        grupo=grupo,
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
    observaciones = request.form.get("observaciones")

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
    estudiante_ids = request.form.getlist("estudiantes[]")
    accion_id = request.form.get("accion_id")
    horas = request.form.get("horas_asistencia", 0.0)
    periodo = request.form.get("periodo")

    if not estudiante_ids or not accion_id or not periodo:
        flash("Debe seleccionar al menos un estudiante, una acción y un período", "error")
        return redirect(url_for("ingesta.index"))

    for est_id in estudiante_ids:
        participacion = ParticipacionAccion(
            estudiante_id=int(est_id),
            accion_id=int(accion_id),
            periodo=periodo,
            horas_asistencia=float(horas)
        )
        db.session.add(participacion)

    db.session.commit()

    meses = desglosar_periodo(periodo)
    indicador = procesar_indicadores_accion(int(accion_id), periodo)

    if indicador:
        if len(meses) > 1:
            flash(f"Semestre {periodo} desglosado en {len(meses)} meses ({meses[0]} a {meses[-1]}): "
                  f"las {horas} hrs de cada uno de los {len(estudiante_ids)} alumnos se repartieron "
                  f"en partes iguales entre los meses. Semáforo: {indicador.estado_semaforo}", "info")
        else:
            flash(f"Motor actualizado para el periodo {periodo}. {len(estudiante_ids)} alumnos cargados "
                  f"({horas} hrs c/u). Semáforo: {indicador.estado_semaforo}", "info")
    else:
        if len(meses) > 1:
            flash(f"Participación guardada para el semestre {periodo}, pero no hay datos de "
                  f"notas/mediciones para calcular indicadores.", "warning")
        else:
            flash(f"Participación guardada para el periodo {periodo}. "
                  f"Faltan datos en App Ponderado para calcular indicadores.",
                  "warning")

    return redirect(url_for("ingesta.index"))
"""Blueprint de configuración del sistema."""
import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.pme import Establecimiento, ConfiguracionSistema
from app.models.user import User

config_bp = Blueprint("config", __name__, template_folder="../templates/configuracion")

ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def _roles_disponibles():
    """Detecta los roles definidos en el modelo User (defensivo)."""
    roles = []
    for attr in ["ROL_ADMIN", "ROL_DIRECTOR", "ROL_SOSTENEDOR", "ROL_UTP", "ROL_ENCARGADO_PME"]:
        rol = getattr(User, attr, None)
        if rol and rol not in roles:
            roles.append(rol)
    return roles or ["Director", "Sostenedor", "UTP", "Encargado PME"]


def _get_or_create_config(establecimiento_id):
    """Devuelve la configuración del establecimiento, creándola con defaults si no existe."""
    config = ConfiguracionSistema.query.filter_by(establecimiento_id=establecimiento_id).first()
    if not config:
        config = ConfiguracionSistema(establecimiento_id=establecimiento_id)
        db.session.add(config)
        db.session.commit()
    return config


@config_bp.route("/")
@login_required
def index():
    establecimiento = Establecimiento.query.first()
    if not establecimiento:
        flash("No hay establecimiento configurado. Ejecute seed.py primero.", "error")
        return redirect(url_for("dashboard.index"))

    config = _get_or_create_config(establecimiento.id)
    usuarios = User.query.filter_by(establecimiento_id=establecimiento.id).all()

    return render_template(
        "configuracion/index.html",
        establecimiento=establecimiento,
        config=config,
        usuarios=usuarios,
        roles=_roles_disponibles(),
    )


# ============================================================
# TAB 1: AJUSTES DEL COLEGIO
# ============================================================

@config_bp.route("/establecimiento", methods=["POST"])
@login_required
def guardar_establecimiento():
    establecimiento = Establecimiento.query.first()
    if not establecimiento:
        return redirect(url_for("config.index"))

    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("El nombre del establecimiento es obligatorio", "error")
        return redirect(url_for("config.index"))

    establecimiento.nombre = nombre
    establecimiento.direccion = request.form.get("direccion", "").strip() or None
    establecimiento.telefono = request.form.get("telefono", "").strip() or None
    establecimiento.email_institucional = request.form.get("email_institucional", "").strip() or None

    db.session.commit()
    flash("Información institucional actualizada correctamente", "success")
    return redirect(url_for("config.index"))


@config_bp.route("/logo", methods=["POST"])
@login_required
def subir_logo():
    establecimiento = Establecimiento.query.first()
    if not establecimiento:
        return redirect(url_for("config.index"))

    file = request.files.get("logo")
    if not file or file.filename == "":
        flash("No se seleccionó ningún archivo", "error")
        return redirect(url_for("config.index"))

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        flash("Formato no permitido. Use PNG, JPG o JPEG", "error")
        return redirect(url_for("config.index"))

    # Guardar SIEMPRE en app/static/uploads (independiente del UPLOAD_FOLDER del config)
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads"
    )
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(f"logo_est_{establecimiento.id}.{ext}")
    file.save(os.path.join(upload_dir, filename))

    establecimiento.logo_url = f"/static/uploads/{filename}"
    db.session.commit()
    flash("Logo actualizado correctamente", "success")
    return redirect(url_for("config.index"))


# ============================================================
# TAB 2: PARÁMETROS DEL ALGORITMO
# ============================================================

@config_bp.route("/algoritmo", methods=["POST"])
@login_required
def guardar_parametros():
    establecimiento = Establecimiento.query.first()
    if not establecimiento:
        return redirect(url_for("config.index"))

    try:
        anio = int(request.form.get("anio_activo", 2026))

        # El formulario envía porcentajes (85, 95) → convertir a 0-1
        um_rojo = float(request.form.get("umbral_rojo", 85)) / 100.0
        um_amar = float(request.form.get("umbral_amarillo", 95)) / 100.0

        peso_r = float(request.form.get("peso_rendimiento", 60)) / 100.0
        peso_a = float(request.form.get("peso_asistencia", 40)) / 100.0
    except (ValueError, TypeError):
        flash("Los parámetros deben ser valores numéricos", "error")
        return redirect(url_for("config.index"))

    # Validaciones de coherencia
    if not (0 < um_rojo < um_amar <= 1.0):
        flash("Umbrales inválidos: Rojo debe ser menor que Amarillo y ambos entre 1% y 100%", "error")
        return redirect(url_for("config.index"))

    if peso_r < 0 or peso_a < 0 or (peso_r + peso_a) == 0:
        flash("Los pesos del IEA deben ser positivos", "error")
        return redirect(url_for("config.index"))

    if not (2000 <= anio <= 2100):
        flash("El año lectivo debe ser válido", "error")
        return redirect(url_for("config.index"))

    config = _get_or_create_config(establecimiento.id)
    config.anio_activo = anio
    config.umbral_rojo = round(um_rojo, 3)
    config.umbral_amarillo = round(um_amar, 3)
    config.peso_rendimiento = round(peso_r, 3)
    config.peso_asistencia = round(peso_a, 3)

    db.session.commit()
    flash("Parámetros del algoritmo actualizados. Los próximos cálculos usarán esta configuración", "success")
    return redirect(url_for("config.index"))


# ============================================================
# TAB 3: GESTIÓN DE USUARIOS
# ============================================================

@config_bp.route("/usuarios", methods=["POST"])
@login_required
def crear_usuario():
    establecimiento = Establecimiento.query.first()
    if not establecimiento:
        return redirect(url_for("config.index"))

    email = request.form.get("email", "").strip().lower()
    nombre = request.form.get("nombre", "").strip()
    rol = request.form.get("rol", "Director")
    password = request.form.get("password", "")

    if not all([email, nombre, password]):
        flash("Nombre, correo y contraseña son obligatorios", "error")
        return redirect(url_for("config.index"))

    if len(password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres", "error")
        return redirect(url_for("config.index"))

    if User.query.filter_by(email=email).first():
        flash(f"El correo {email} ya está registrado", "error")
        return redirect(url_for("config.index"))

    try:
        nuevo = User(
            email=email,
            nombre=nombre,
            rol=rol,
            activo=True,
            establecimiento_id=establecimiento.id,
        )
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        flash(f"Usuario {nombre} creado exitosamente con rol {rol}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear el usuario: {str(e)}", "error")

    return redirect(url_for("config.index"))


@config_bp.route("/usuarios/<int:usuario_id>/toggle", methods=["POST"])
@login_required
def toggle_usuario(usuario_id):
    usuario = User.query.get_or_404(usuario_id)

    # Protección: no puedes desactivarte a ti mismo
    if usuario.id == current_user.id:
        flash("No puede desactivar su propia cuenta", "error")
        return redirect(url_for("config.index"))

    usuario.activo = not usuario.activo
    estado = "activado" if usuario.activo else "desactivado"
    db.session.commit()
    flash(f"Usuario {usuario.nombre} {estado}", "info")
    return redirect(url_for("config.index"))
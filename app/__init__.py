"""Application Factory para EduGest PME."""
from flask import Flask
import os


def create_app(config_name="default"):
    """Crea y configura la instancia de la aplicación Flask."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Carga configuración según entorno
    from app.config import config_por_entorno
    app.config.from_object(config_por_entorno.get(config_name, config_por_entorno["default"]))

    # Asegura directorio de uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Inicializa extensiones
    from app.extensions import db, login_manager
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor inicie sesión para acceder."
    login_manager.login_message_category = "info"

    # Registro de blueprints
    _registrar_blueprints(app)

    # Crear tablas si no existen
    with app.app_context():
        # CAMBIO CLAVE: Importar todos los modelos aquí para que SQLAlchemy los reconozca
        from app.models.user import User
        from app.models.pme import Establecimiento, DimensionPME, ObjetivoPME, AccionPME, Curso
        from app.models.metrics import Estudiante, RegistroAppPonderado, MetricaSIGE, ParticipacionAccion, IndicadorAccion
        
        db.create_all()

    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        return json.loads(value)
    return app


def _registrar_blueprints(app):
    """Registra todos los blueprints del sistema."""
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.ingesta import ingesta_bp
    from app.routes.acciones import acciones_bp
    from app.routes.reportes import reportes_bp
    from app.routes.config import config_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(ingesta_bp, url_prefix="/ingesta")
    app.register_blueprint(acciones_bp, url_prefix="/acciones")
    app.register_blueprint(reportes_bp, url_prefix="/reportes")
    app.register_blueprint(config_bp, url_prefix="/configuracion")

    # Ruta raíz redirige al login
    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("auth.login"))
"""Application Factory para EduGest PME."""
from flask import Flask
from app.models import pme, metrics, user
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
        from app.models.metrics import (Estudiante, RegistroAppPonderado, MetricaSIGE,
                                        ParticipacionAccion, IndicadorAccion,
                                        DefinicionIndicador, MedicionIndicador)  # <-- NUEVOS

        db.create_all()

        # Migraciones ligeras: create_all() no agrega columnas a tablas que
        # ya existen. Se asegura que todas las columnas definidas en los
        # modelos estén presentes en las tablas físicas (idempotente, no
        # borra datos). Esto permite actualizar una base de datos antigua
        # sin necesidad de recrearla.
        _asegurar_columnas_faltantes()
        db.session.commit()

    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        return json.loads(value)
    return app


def _asegurar_columna(tabla, columna, ddl):
    """Agrega una columna faltante a una tabla ya existente (idempotente)."""
    from sqlalchemy import inspect, text
    from app.extensions import db

    insp = inspect(db.engine)
    if not insp.has_table(tabla):
        return
    columnas = [c["name"] for c in insp.get_columns(tabla)]
    if columna not in columnas:
        db.session.execute(text(ddl))


def _asegurar_columnas_faltantes():
    """Agrega a cada tabla existente las columnas que falten según los modelos.

    `db.create_all()` crea tablas nuevas pero no altera las existentes. Esta
    función compara el esquema de SQLAlchemy con el de la base de datos y
    ejecuta `ALTER TABLE ... ADD COLUMN` por cada columna faltante, de forma
    idempotente y sin borrar datos. Si una columna no puede agregarse (por
    ejemplo, NOT NULL sin valor por defecto en SQLite), se omite con un
    aviso en lugar de romper el arranque.
    """
    from sqlalchemy import inspect, text
    from app.extensions import db

    insp = inspect(db.engine)
    for table_name, table in db.metadata.tables.items():
        if not insp.has_table(table_name):
            continue
        existentes = {c["name"] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name in existentes:
                continue
            try:
                tipo_sql = col.type.compile(dialect=db.engine.dialect)
            except Exception:
                tipo_sql = "TEXT"
            ddl = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {tipo_sql}"
            try:
                db.session.execute(text(ddl))
                print(f"  -> columna agregada: {table_name}.{col.name}")
            except Exception as exc:
                db.session.rollback()
                print(f"  -> no se pudo agregar {table_name}.{col.name}: {exc}")


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
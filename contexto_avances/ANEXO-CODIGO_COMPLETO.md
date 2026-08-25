# ANEXO - Código Fuente Completo del Proyecto

> **ADVERTENCIA:** Este archivo es muy largo. Contiene TODO el código fuente del proyecto EduGest PME tal como está en la fecha del snapshot.
> Úsalo para referencia rápida sin necesidad de abrir archivos individuales.

---

## `app/__init__.py`

```python
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

    # IMPORTANTE: Importar User para registrar el user_loader de Flask-Login
    from app.models.user import User  # noqa: F401

    # Registro de blueprints
    _registrar_blueprints(app)

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

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

```

---

## `app/config.py`

```python
"""Configuración centralizada de la aplicación EduGest PME."""
import os
from datetime import timedelta


class Config:
    """Configuración base compartida por todos los entornos."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "edugest-dev-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///edugest_pme.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Parámetros del algoritmo PME
    UMBRAL_SEMAFORO_ROJO = 0.85
    UMBRAL_SEMAFORO_AMARILLO = 0.95
    UMBRAL_SEMAFORO_VERDE = 1.0

    # Configuración de carga de archivos
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False


class TestingConfig(Config):
    """Configuración para pruebas unitarias."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_por_entorno = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

```

---

## `app/extensions.py`

```python
"""Extensiones de Flask centralizadas para evitar imports circulares."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

```

---

## `app/models/__init__.py`

```python
"""Paquete de modelos SQLAlchemy para EduGest PME."""
from app.extensions import db

# Importa todos los modelos para que SQLAlchemy los registre
from app.models.user import User
from app.models.pme import (
    Establecimiento,
    DimensionPME,
    ObjetivoPME,
    AccionPME,
    Curso,
)
from app.models.metrics import (
    Estudiante,
    RegistroAppPonderado,
    MetricaSIGE,
    ParticipacionAccion,
    IndicadorAccion,
)

__all__ = [
    "db",
    "User",
    "Establecimiento",
    "DimensionPME",
    "ObjetivoPME",
    "AccionPME",
    "Curso",
    "Estudiante",
    "RegistroAppPonderado",
    "MetricaSIGE",
    "ParticipacionAccion",
    "IndicadorAccion",
]

```

---

## `app/models/metrics.py`

```python
"""Modelos de métricas, datos SIGE y App Ponderado."""
from datetime import datetime
from app.extensions import db


class Estudiante(db.Model):
    """Estudiante matriculado en el establecimiento."""

    __tablename__ = "estudiantes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(30), unique=True, nullable=False, index=True)

    curso_id = db.Column(db.Integer, db.ForeignKey("cursos.id"), nullable=False)
    establecimiento_id = db.Column(
        db.Integer, db.ForeignKey("establecimientos.id"), nullable=False
    )

    activo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    curso = db.relationship("Curso", back_populates="estudiantes")
    establecimiento = db.relationship("Establecimiento", back_populates="estudiantes")
    registros_app = db.relationship(
        "RegistroAppPonderado", back_populates="estudiante", lazy="dynamic"
    )
    participaciones = db.relationship(
        "ParticipacionAccion", back_populates="estudiante", lazy="dynamic"
    )

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def __repr__(self):
        return f"<Estudiante {self.nombre_completo}>"


class RegistroAppPonderado(db.Model):
    """Datos de rendimiento y asistencia provenientes de App Ponderado (F-2)."""

    __tablename__ = "registros_app_ponderado"

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(
        db.Integer, db.ForeignKey("estudiantes.id"), nullable=False
    )

    # Periodo: formato "2026-03" (año-mes) o "2026-T1" (trimestre)
    periodo = db.Column(db.String(10), nullable=False, index=True)
    asignatura = db.Column(db.String(50), nullable=False)

    # Métricas académicas
    promedio_notas = db.Column(db.Float, nullable=False)
    porcentaje_asistencia = db.Column(db.Float, nullable=False)

    # Bitácora de ejecución física de la acción PME
    bitacora = db.Column(db.Text, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    estudiante = db.relationship("Estudiante", back_populates="registros_app")

    def __repr__(self):
        return f"<RegistroApp {self.estudiante_id} - {self.periodo}>"


class MetricaSIGE(db.Model):
    """Métricas oficiales consolidadas del SIGE (F-3)."""

    __tablename__ = "metricas_sige"

    id = db.Column(db.Integer, primary_key=True)
    establecimiento_id = db.Column(
        db.Integer, db.ForeignKey("establecimientos.id"), nullable=False
    )

    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)

    matricula_oficial = db.Column(db.Integer, nullable=False)
    asistencia_oficial_validada = db.Column(db.Float, nullable=False)
    calificaciones_consolidadas = db.Column(db.Float, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    establecimiento = db.relationship("Establecimiento", back_populates="metricas_sige")

    def __repr__(self):
        return f"<MetricaSIGE {self.anio}-{self.mes:02d}>"


class ParticipacionAccion(db.Model):
    """Seguimiento de participantes por acción PME (F-4)."""

    __tablename__ = "participaciones_accion"

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(
        db.Integer, db.ForeignKey("estudiantes.id"), nullable=False
    )
    accion_id = db.Column(
        db.Integer, db.ForeignKey("acciones_pme.id"), nullable=False
    )

    horas_asistencia = db.Column(db.Float, default=0.0, nullable=False)
    asistencia_talleres = db.Column(db.Integer, default=0, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    estudiante = db.relationship("Estudiante", back_populates="participaciones")
    accion = db.relationship("AccionPME", back_populates="participaciones")

    def __repr__(self):
        return f"<Participacion E:{self.estudiante_id} A:{self.accion_id}>"


class IndicadorAccion(db.Model):
    """Indicadores calculados mensualmente por acción (IEA, Pearson, Semáforo)."""

    __tablename__ = "indicadores_accion"

    id = db.Column(db.Integer, primary_key=True)
    accion_id = db.Column(
        db.Integer, db.ForeignKey("acciones_pme.id"), nullable=False
    )

    # Periodo
    mes = db.Column(db.String(10), nullable=False)  # formato "2026-03"

    # Índice de Eficiencia de Acción (IEA)
    iea = db.Column(db.Float, nullable=True)

    # Correlación de Pearson
    correlacion_pearson = db.Column(db.Float, nullable=True)

    # Semáforo: Rojo, Amarillo, Verde
    estado_semaforo = db.Column(db.String(20), nullable=True)

    # Proyección de cumplimiento (0.0 - 1.0+)
    proyeccion_cumplimiento = db.Column(db.Float, nullable=True)

    # Gasto del mes
    gasto_mes = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    accion = db.relationship("AccionPME", back_populates="indicadores")

    def __repr__(self):
        return f"<IndicadorAccion A:{self.accion_id} M:{self.mes}>"

```

---

## `app/models/pme.py`

```python
"""Modelos del Plan de Mejoramiento Educativo (PME)."""
from datetime import datetime
from app.extensions import db


class Establecimiento(db.Model):
    """Representa un establecimiento educacional."""

    __tablename__ = "establecimientos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    rbd = db.Column(db.String(20), unique=True, nullable=False, index=True)
    direccion = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    email_institucional = db.Column(db.String(120), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    usuarios = db.relationship("User", back_populates="establecimiento", lazy="dynamic")
    cursos = db.relationship("Curso", back_populates="establecimiento", lazy="dynamic")
    metricas_sige = db.relationship("MetricaSIGE", back_populates="establecimiento", lazy="dynamic")
    estudiantes = db.relationship("Estudiante", back_populates="establecimiento", lazy="dynamic")

    def __repr__(self):
        return f"<Establecimiento {self.nombre} (RBD: {self.rbd})>"


class DimensionPME(db.Model):
    """Las 4 dimensiones oficiales del PME."""

    __tablename__ = "dimensiones_pme"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0, nullable=False)

    # Relaciones
    objetivos = db.relationship("ObjetivoPME", back_populates="dimension", lazy="dynamic")

    # Constantes de dimensiones
    GESTION_PEDAGOGICA = "Gestión Pedagógica"
    LIDERAZGO_ESCOLAR = "Liderazgo Escolar"
    CONVIVENCIA_ESCOLAR = "Convivencia Escolar"
    GESTION_RECURSOS = "Gestión de Recursos"

    def __repr__(self):
        return f"<DimensionPME {self.nombre}>"


class ObjetivoPME(db.Model):
    """Objetivos estratégicos dentro de una dimensión PME."""

    __tablename__ = "objetivos_pme"

    id = db.Column(db.Integer, primary_key=True)
    dimension_id = db.Column(
        db.Integer, db.ForeignKey("dimensiones_pme.id"), nullable=False
    )
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    anio = db.Column(db.Integer, nullable=False, default=2026)
    estado = db.Column(db.String(30), default="Activo", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    dimension = db.relationship("DimensionPME", back_populates="objetivos")
    acciones = db.relationship("AccionPME", back_populates="objetivo", lazy="dynamic")

    def __repr__(self):
        return f"<ObjetivoPME {self.nombre[:40]}...>"


class AccionPME(db.Model):
    """Acciones concretas del PME con presupuesto, metas y seguimiento."""

    __tablename__ = "acciones_pme"

    id = db.Column(db.Integer, primary_key=True)
    objetivo_id = db.Column(
        db.Integer, db.ForeignKey("objetivos_pme.id"), nullable=False
    )
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Presupuesto
    presupuesto_asignado = db.Column(db.Float, default=0.0, nullable=False)
    presupuesto_ejecutado = db.Column(db.Float, default=0.0, nullable=False)

    # Estados: Planificada, En Ejecución, Finalizada, Cancelada
    estado = db.Column(db.String(30), default="Planificada", nullable=False)
    responsable = db.Column(db.String(100), nullable=True)

    # Fechas
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)

    # Metas
    meta_cualitativa = db.Column(db.Text, nullable=True)
    meta_cuantitativa = db.Column(db.String(100), nullable=True)
    indicador_medible = db.Column(db.String(100), nullable=True)
    curso_objetivo = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    objetivo = db.relationship("ObjetivoPME", back_populates="acciones")
    participaciones = db.relationship(
        "ParticipacionAccion", back_populates="accion", lazy="dynamic"
    )
    indicadores = db.relationship(
        "IndicadorAccion", back_populates="accion", lazy="dynamic"
    )

    def porcentaje_ejecucion_presupuesto(self):
        """Calcula el % de ejecución presupuestaria."""
        if self.presupuesto_asignado <= 0:
            return 0.0
        return min(100.0, (self.presupuesto_ejecutado / self.presupuesto_asignado) * 100)

    def __repr__(self):
        return f"<AccionPME {self.nombre[:40]}...>"


class Curso(db.Model):
    """Cursos o niveles del establecimiento educacional."""

    __tablename__ = "cursos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    nivel = db.Column(db.String(50), nullable=False)
    anio = db.Column(db.Integer, nullable=False, default=2026)
    establecimiento_id = db.Column(
        db.Integer, db.ForeignKey("establecimientos.id"), nullable=False
    )

    # Relaciones
    establecimiento = db.relationship("Establecimiento", back_populates="cursos")
    estudiantes = db.relationship("Estudiante", back_populates="curso", lazy="dynamic")

    def __repr__(self):
        return f"<Curso {self.nombre}>"

```

---

## `app/models/user.py`

```python
"""Modelo de usuario y autenticación para EduGest PME."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """Representa un usuario del sistema EduGest PME."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default="Encargado PME")
    activo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con establecimiento
    establecimiento_id = db.Column(
        db.Integer, db.ForeignKey("establecimientos.id"), nullable=True
    )
    establecimiento = db.relationship("Establecimiento", back_populates="usuarios")

    # Constantes de roles permitidos
    ROL_DIRECTOR = "Director"
    ROL_UTP = "UTP"
    ROL_ENCARGADO_PME = "Encargado PME"
    ROL_SOSTENEDOR = "Sostenedor"
    ROL_ADMIN = "Administrador"

    ROLES_VALIDOS = [
        ROL_DIRECTOR,
        ROL_UTP,
        ROL_ENCARGADO_PME,
        ROL_SOSTENEDOR,
        ROL_ADMIN,
    ]

    def set_password(self, password):
        """Genera y almacena el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def es_admin(self):
        """Retorna True si el usuario tiene rol de administrador o director."""
        return self.rol in (self.ROL_ADMIN, self.ROL_DIRECTOR)

    def es_sostenedor(self):
        """Retorna True si el usuario es sostenedor."""
        return self.rol == self.ROL_SOSTENEDOR

    def __repr__(self):
        return f"<User {self.email} ({self.rol})>"


@login_manager.user_loader
def load_user(user_id):
    """Callback requerido por Flask-Login para cargar usuarios por ID."""
    return User.query.get(int(user_id))

```

---

## `app/routes/__init__.py`

```python

```

---

## `app/routes/acciones.py`

```python
"""Blueprint de acciones PME."""
from flask import Blueprint, render_template
from flask_login import login_required

acciones_bp = Blueprint("acciones", __name__, template_folder="../templates/acciones")


@acciones_bp.route("/")
@login_required
def index():
    return render_template("acciones/index.html")

```

---

## `app/routes/auth.py`

```python
"""Blueprint de autenticación."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Muestra el formulario de login y procesa la autenticación."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email, activo=True).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido, {user.nombre}", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash("Credenciales incorrectas. Intente nuevamente.", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesión del usuario."""
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))

```

---

## `app/routes/config.py`

```python
"""Blueprint de configuración."""
from flask import Blueprint, render_template
from flask_login import login_required

config_bp = Blueprint("config", __name__, template_folder="../templates/configuracion")


@config_bp.route("/")
@login_required
def index():
    return render_template("configuracion/index.html")

```

---

## `app/routes/dashboard.py`

```python
"""Blueprint del dashboard."""
from flask import Blueprint, render_template
from flask_login import login_required

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html")

```

---

## `app/routes/ingesta.py`

```python
"""Blueprint de ingesta de datos."""
from flask import Blueprint, render_template
from flask_login import login_required

ingesta_bp = Blueprint("ingesta", __name__, template_folder="../templates/ingesta")


@ingesta_bp.route("/")
@login_required
def index():
    return render_template("ingesta/index.html")

```

---

## `app/routes/reportes.py`

```python
"""Blueprint de reportes."""
from flask import Blueprint, render_template
from flask_login import login_required

reportes_bp = Blueprint("reportes", __name__, template_folder="../templates/reportes")


@reportes_bp.route("/")
@login_required
def index():
    return render_template("reportes/index.html")

```

---

## `app/services/__init__.py`

```python

```

---

## `app/services/data_loader.py`

```python
"""Procesamiento de cargas manuales y archivos CSV/Excel."""
import pandas as pd
from io import BytesIO


def procesar_csv_acciones(file_stream):
    """Procesa un archivo CSV con registros de acciones PME (F-1)."""
    try:
        df = pd.read_csv(file_stream)
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}


def procesar_excel_metricas(file_stream):
    """Procesa un archivo Excel con métricas SIGE o App Ponderado."""
    try:
        df = pd.read_excel(BytesIO(file_stream.read()))
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}

```

---

## `app/services/pme_engine.py`

```python
"""Motor algorítmico de cálculo cuantitativo PME.

Incluye:
- Índice de Eficiencia de Acción (IEA)
- Correlación de Pearson
- Algoritmo de Semáforo / Proyección de Cumplimiento
"""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia):
    """Calcula el Índice de Eficiencia de Acción (IEA).

    Fórmula conceptual: impacto generado / recurso invertido.
    Retorna valor entre 0.0 y 5.0.
    """
    if gasto_ejecutado <= 0 or horas_ejecutadas <= 0:
        return 0.0

    impacto = (delta_rendimiento * 0.6) + (delta_asistencia * 0.4)
    recurso = (gasto_ejecutado / 1_000_000) + (horas_ejecutadas / 10)
    iea = min(5.0, max(0.0, (impacto / recurso) * 10))
    return round(iea, 2)


def calcular_correlacion_pearson(x, y):
    """Calcula el coeficiente de correlación de Pearson entre dos arrays.

    Args:
        x: Array de valores (ej. horas de asistencia a taller).
        y: Array de valores (ej. mejora en notas).

    Returns:
        tuple: (coeficiente_r, valor_p)
    """
    if len(x) < 2 or len(y) < 2 or len(x) != len(y):
        return None, None
    try:
        r, p = pearsonr(x, y)
        return round(r, 3), round(p, 4)
    except Exception:
        return None, None


def determinar_semaforo(proyeccion_cumplimiento, umbral_rojo=0.85, umbral_amarillo=0.95):
    """Determina el estado del semáforo según proyección de cumplimiento.

    Args:
        proyeccion_cumplimiento: Valor entre 0.0 y 1.0+
        umbral_rojo: Límite inferior (default 0.85)
        umbral_amarillo: Límite medio (default 0.95)

    Returns:
        str: "Rojo", "Amarillo" o "Verde"
    """
    if proyeccion_cumplimiento < umbral_rojo:
        return "Rojo"
    elif proyeccion_cumplimiento < umbral_amarillo:
        return "Amarillo"
    return "Verde"


def proyectar_cumplimiento(valores_historicos, meta):
    """Proyecta el cumplimiento a fin de año usando regresión lineal simple.

    Args:
        valores_historicos: Lista de valores mensuales acumulados.
        meta: Valor objetivo a alcanzar.

    Returns:
        float: Proyección de cumplimiento (0.0 - 1.0+)
    """
    if not valores_historicos or meta <= 0:
        return 0.0

    n = len(valores_historicos)
    if n < 2:
        return min(1.0, valores_historicos[-1] / meta) if valores_historicos else 0.0

    x = np.arange(n)
    y = np.array(valores_historicos)

    # Regresión lineal: y = mx + b
    m, b = np.polyfit(x, y, 1)

    # Proyectar al mes 12 (índice 11, 0-based)
    proyeccion = m * 11 + b
    cumplimiento = proyeccion / meta

    return round(min(2.0, max(0.0, cumplimiento)), 3)

```

---

## `app/templates/acciones/index.html`

```html
{% extends "layouts/base.html" %}

{% block title %}Acciones PME - EduGest{% endblock %}

{% block content %}
<div class="p-8">
    <!-- Breadcrumb -->
    <div class="mb-6">
        <a href="/acciones/" class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-2">
            <i class="fas fa-arrow-left"></i> Volver a Acciones PME
        </a>
    </div>

    <!-- Header Card -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-8">
        <div class="flex flex-col lg:flex-row">
            <!-- Image -->
            <div class="lg:w-1/3 h-64 lg:h-auto bg-gradient-to-br from-indigo-600 to-purple-700 relative">
                <img src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=600&q=80" 
                     alt="Matemáticas" class="w-full h-full object-cover opacity-40">
                <div class="absolute bottom-4 left-4">
                    <span class="bg-white/90 text-indigo-700 text-xs font-bold px-3 py-1 rounded-full">ID: ACC-123</span>
                </div>
            </div>
            <!-- Info -->
            <div class="lg:w-2/3 p-8">
                <h1 class="text-3xl font-bold text-gray-900 mb-4">Taller de Refuerzo Matemático<br>8vo Básico</h1>
                <span class="inline-flex items-center gap-2 bg-cyan-100 text-cyan-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
                    <i class="fas fa-check-circle"></i> En Ejecución
                </span>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
                    <div>
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Presupuesto Asignado</p>
                        <div class="flex items-center gap-2">
                            <i class="fas fa-money-check-alt text-indigo-600"></i>
                            <span class="text-xl font-bold text-gray-900">$2.500.000</span>
                        </div>
                    </div>
                    <div>
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Responsable</p>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 text-xs">
                                <i class="fas fa-user"></i>
                            </div>
                            <span class="text-gray-900 font-medium">Prof. Marta Díaz</span>
                        </div>
                    </div>
                    <div>
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Fecha Inicio - Fin</p>
                        <span class="text-gray-900 font-medium">Mar 2024 - Nov 2024</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Analytics Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <!-- Analítica de Impacto -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
            <div class="flex items-center gap-2 mb-6">
                <i class="fas fa-chart-line text-indigo-600"></i>
                <h3 class="text-lg font-semibold text-gray-900">Analítica de Impacto</h3>
            </div>

            <div class="flex flex-col items-center mb-6">
                <div class="relative w-32 h-32">
                    <svg class="w-32 h-32 transform -rotate-90">
                        <circle cx="64" cy="64" r="56" stroke="#e5e7eb" stroke-width="8" fill="none"/>
                        <circle cx="64" cy="64" r="56" stroke="#3b82f6" stroke-width="8" fill="none"
                                stroke-dasharray="351.86" stroke-dashoffset="63.33" stroke-linecap="round"/>
                    </svg>
                    <div class="absolute inset-0 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-gray-900">0.82</span>
                        <span class="text-xs text-gray-500">Valor r</span>
                    </div>
                </div>
            </div>

            <p class="text-center text-sm text-gray-600 leading-relaxed mb-4">
                Existe una correlación <span class="text-cyan-600 font-semibold">fuerte</span>: a mayor asistencia al taller, mejores resultados en evaluaciones.
            </p>

            <div class="flex items-center justify-between pt-4 border-t border-gray-100">
                <span class="text-xs text-gray-500">Métrica: Correlación de Pearson</span>
                <i class="far fa-question-circle text-gray-400"></i>
            </div>
        </div>

        <!-- Comparativa Rendimiento -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center gap-2">
                    <i class="fas fa-chart-bar text-indigo-600"></i>
                    <h3 class="text-lg font-semibold text-gray-900">Comparativa Rendimiento</h3>
                </div>
                <div class="flex items-center gap-4 text-xs">
                    <span class="flex items-center gap-1.5">
                        <span class="w-3 h-3 bg-indigo-600 rounded-sm"></span> Grupo Beneficiado
                    </span>
                    <span class="flex items-center gap-1.5">
                        <span class="w-3 h-3 bg-gray-300 rounded-sm"></span> Grupo Control
                    </span>
                </div>
            </div>

            <div class="h-64 flex items-end justify-around gap-4 pb-6 border-b border-gray-200">
                <!-- Diagnóstico -->
                <div class="flex flex-col items-center gap-2 flex-1">
                    <div class="flex items-end gap-3 w-full justify-center" style="height: 140px;">
                        <div class="w-10 bg-gray-300 rounded-t" style="height: 70%;"></div>
                        <div class="w-10 bg-indigo-600 rounded-t" style="height: 80%;"></div>
                    </div>
                    <span class="text-xs text-gray-600 font-medium">Diagnóstico</span>
                </div>
                <!-- Semestre 1 -->
                <div class="flex flex-col items-center gap-2 flex-1">
                    <div class="flex items-end gap-3 w-full justify-center" style="height: 180px;">
                        <div class="w-10 bg-gray-300 rounded-t" style="height: 65%;"></div>
                        <div class="w-10 bg-indigo-600 rounded-t" style="height: 85%;"></div>
                    </div>
                    <span class="text-xs text-gray-600 font-medium">Semestre 1</span>
                </div>
                <!-- Semestre 2 -->
                <div class="flex flex-col items-center gap-2 flex-1">
                    <div class="flex items-end gap-3 w-full justify-center" style="height: 200px;">
                        <div class="w-10 bg-gray-300 rounded-t" style="height: 60%;"></div>
                        <div class="w-10 bg-indigo-600 rounded-t" style="height: 95%;"></div>
                    </div>
                    <span class="text-xs text-gray-600 font-medium">Semestre 2</span>
                </div>
            </div>
            <div class="flex justify-between text-xs text-gray-400 mt-2">
                <span>4.0</span>
                <span>5.5</span>
                <span>7.0</span>
            </div>
        </div>
    </div>

    <!-- Indicadores Afectados -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
        <div class="flex items-center gap-2 mb-6">
            <i class="fas fa-bullseye text-indigo-600"></i>
            <h3 class="text-lg font-semibold text-gray-900">Indicadores Afectados</h3>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="p-4 border border-gray-200 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Promedio Matemáticas</p>
                <p class="text-lg font-bold text-gray-900">5.8 <span class="text-xs text-green-600 font-normal">↑ +0.8</span></p>
            </div>
            <div class="p-4 border border-gray-200 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">% Asistencia</p>
                <p class="text-lg font-bold text-gray-900">94.2% <span class="text-xs text-green-600 font-normal">↑ +3.2%</span></p>
            </div>
            <div class="p-4 border border-gray-200 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Participación</p>
                <p class="text-lg font-bold text-gray-900">87% <span class="text-xs text-gray-400 font-normal">meta: 90%</span></p>
            </div>
            <div class="p-4 border border-gray-200 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Satisfacción</p>
                <p class="text-lg font-bold text-gray-900">4.5/5 <span class="text-xs text-green-600 font-normal">↑ +0.3</span></p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

---

## `app/templates/auth/login.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inicio de Sesión - EduGest PME</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="flex h-screen">
    <!-- Left Panel -->
    <div class="w-1/2 relative hidden lg:block">
        <img src="https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1200&q=80" 
             alt="EduGest" class="absolute inset-0 w-full h-full object-cover">
        <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
        <div class="absolute bottom-0 left-0 p-12 text-white">
            <div class="flex items-center gap-3 mb-6">
                <i class="fas fa-school text-3xl"></i>
                <h1 class="text-2xl font-bold">EduGest</h1>
            </div>
            <h2 class="text-4xl font-bold mb-4 leading-tight">Sistema de Medición<br>Cuantitativa y Proyección<br>PME</h2>
            <p class="text-lg text-gray-200">Gestión institucional eficiente basada en datos para el desarrollo educativo continuo.</p>
        </div>
    </div>

    <!-- Right Panel -->
    <div class="w-full lg:w-1/2 flex items-center justify-center bg-white p-8">
        <div class="w-full max-w-md">
            <h2 class="text-3xl font-bold text-gray-900 mb-2">Bienvenido</h2>
            <p class="text-gray-500 mb-8">Ingrese sus credenciales para acceder al sistema.</p>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                <div class="mb-4 space-y-2">
                  {% for category, message in messages %}
                    <div class="px-4 py-3 rounded-lg text-sm 
                      {% if category == 'success' %}bg-green-50 text-green-700 border border-green-200
                      {% elif category == 'danger' %}bg-red-50 text-red-700 border border-red-200
                      {% else %}bg-blue-50 text-blue-700 border border-blue-200{% endif %}">
                      {{ message }}
                    </div>
                  {% endfor %}
                </div>
              {% endif %}
            {% endwith %}

            <form method="POST" action="{{ url_for('auth.login') }}" class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Correo Institucional</label>
                    <div class="relative">
                        <i class="fas fa-envelope absolute left-3.5 top-3.5 text-gray-400 text-sm"></i>
                        <input type="email" name="email" placeholder="usuario@institucion.edu" 
                               class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm"
                               value="admin@liceo.cl">
                    </div>
                </div>

                <div>
                    <div class="flex justify-between items-center mb-1.5">
                        <label class="text-sm font-medium text-gray-700">Contraseña</label>
                        <a href="#" class="text-sm text-indigo-600 hover:text-indigo-800">¿Olvidó su contraseña?</a>
                    </div>
                    <div class="relative">
                        <i class="fas fa-lock absolute left-3.5 top-3.5 text-gray-400 text-sm"></i>
                        <input type="password" name="password" placeholder="••••••••" 
                               class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm"
                               value="admin123">
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Establecimiento Educativo</label>
                    <div class="relative">
                        <i class="fas fa-building absolute left-3.5 top-3.5 text-gray-400 text-sm"></i>
                        <select class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm appearance-none bg-white">
                            <option>Liceo de Excelencia</option>
                        </select>
                        <i class="fas fa-chevron-down absolute right-3.5 top-3.5 text-gray-400 text-xs pointer-events-none"></i>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Año Lectivo</label>
                    <div class="relative">
                        <i class="fas fa-calendar absolute left-3.5 top-3.5 text-gray-400 text-sm"></i>
                        <select class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm appearance-none bg-white">
                            <option>Año Lectivo 2026</option>
                        </select>
                        <i class="fas fa-chevron-down absolute right-3.5 top-3.5 text-gray-400 text-xs pointer-events-none"></i>
                    </div>
                </div>

                <button type="submit" 
                        class="w-full bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition flex items-center justify-center gap-2">
                    Iniciar Sesión <i class="fas fa-arrow-right text-sm"></i>
                </button>
            </form>

            <div class="mt-8 pt-6 border-t border-gray-200 text-center">
                <p class="text-sm text-gray-500">
                    ¿Necesita ayuda? Contacte al <a href="#" class="text-indigo-600 hover:text-indigo-800 font-medium">Soporte Técnico</a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>

```

---

## `app/templates/configuracion/index.html`

```html
{% extends "layouts/base.html" %}

{% block title %}Configuración - EduGest PME{% endblock %}

{% block content %}
<div class="p-8">
    <!-- Header -->
    <div class="flex justify-between items-center mb-8">
        <div class="relative flex-1 max-w-md">
            <i class="fas fa-search absolute left-3 top-3 text-gray-400 text-sm"></i>
            <input type="text" placeholder="Buscar en configuración..." 
                   class="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
        </div>
        <div class="flex items-center gap-3 ml-4">
            <div class="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-gray-300 text-sm">
                <i class="far fa-calendar text-gray-500"></i>
                <span>Academic Year 2024</span>
            </div>
            <button class="w-9 h-9 bg-white rounded-lg border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50 relative">
                <i class="far fa-bell"></i>
                <span class="absolute top-2 right-2.5 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <button class="w-9 h-9 bg-white rounded-lg border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50">
                <i class="far fa-calendar"></i>
            </button>
            <button class="w-9 h-9 bg-white rounded-lg border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50">
                <i class="far fa-user"></i>
            </button>
        </div>
    </div>

    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Configuración del Sistema y Parámetros del Algoritmo</h1>
        <p class="text-gray-500">Gestione las preferencias institucionales, umbrales de alerta y permisos de usuario.</p>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 mb-8">
        <nav class="flex gap-8">
            <a href="#" class="pb-3 border-b-2 border-indigo-600 text-indigo-700 font-medium text-sm">Ajustes del Colegio</a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">Parámetros del Algoritmo</a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">Gestión de Usuarios y Roles</a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">Integraciones</a>
        </nav>
    </div>

    <!-- Información Institucional -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8 max-w-5xl">
        <h2 class="text-xl font-bold text-gray-900 mb-6">Información Institucional</h2>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Logo Upload -->
            <div class="lg:col-span-1">
                <div class="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center bg-gray-50 hover:border-indigo-400 transition cursor-pointer h-64 flex flex-col items-center justify-center">
                    <div class="w-20 h-20 bg-white rounded-lg shadow-sm flex items-center justify-center mb-4">
                        <img src="https://via.placeholder.com/60x60/4F46E5/FFFFFF?text=EG" alt="Logo" class="w-16 h-16 object-contain">
                    </div>
                    <p class="text-indigo-700 font-medium text-sm mb-1 flex items-center gap-2">
                        <i class="fas fa-upload"></i> Cambiar Logo
                    </p>
                    <p class="text-xs text-gray-500">PNG, JPG hasta 2MB</p>
                </div>
            </div>

            <!-- Formulario -->
            <div class="lg:col-span-2 space-y-5">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Nombre del Establecimiento</label>
                        <input type="text" value="Liceo Bicentenario de Excelencia" 
                               class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Rol Base de Datos (RDB)</label>
                        <input type="text" value="12345-6" 
                               class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-gray-50 text-gray-500 cursor-not-allowed" readonly>
                        <p class="text-xs text-gray-500 mt-1">El RDB es inmutable una vez configurado.</p>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Dirección Principal</label>
                    <input type="text" value="Av. Libertador Bernardo O'Higgins 1234, Santiago" 
                           class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Teléfono de Contacto</label>
                        <input type="text" value="+56 2 2123 4567" 
                               class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Correo Electrónico Institucional</label>
                        <input type="email" value="contacto@liceobicentenario.edu.cl" 
                               class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                    </div>
                </div>

                <div class="flex justify-end pt-4">
                    <button type="button" class="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition">
                        Guardar Cambios
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

---

## `app/templates/dashboard/index.html`

```html
{% extends "layouts/base.html" %}

{% block title %}Dashboard - EduGest PME{% endblock %}

{% block content %}
<div class="p-8">
    <!-- Header -->
    <div class="flex justify-between items-start mb-8">
        <div>
            <h1 class="text-3xl font-bold text-gray-900">Cuadro de Mando PME 2026</h1>
            <p class="text-gray-500 mt-1">Visión general del estado y avance del Plan de Mejoramiento Educativo.</p>
        </div>
        <div class="flex items-center gap-3">
            <div class="relative">
                <i class="fas fa-search absolute left-3 top-3 text-gray-400 text-sm"></i>
                <input type="text" placeholder="Search..." class="pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none w-64">
            </div>
            <div class="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-gray-300 text-sm">
                <i class="far fa-calendar text-gray-500"></i>
                <span>Academic Year 2026</span>
            </div>
            <button class="w-9 h-9 bg-white rounded-lg border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50">
                <i class="far fa-bell"></i>
            </button>
            <button class="w-9 h-9 bg-white rounded-lg border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50">
                <i class="far fa-user"></i>
            </button>
        </div>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <div class="flex justify-between items-start mb-4">
                <div class="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600">
                    <i class="fas fa-money-bill-wave"></i>
                </div>
                <span class="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">Anual</span>
            </div>
            <p class="text-sm text-gray-500 mb-1">Presupuesto PME</p>
            <p class="text-2xl font-bold text-gray-900">$120M <span class="text-sm font-normal text-gray-400">/ $150M</span></p>
            <div class="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-indigo-600 rounded-full" style="width: 80%"></div>
            </div>
        </div>

        <div class="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <div class="flex justify-between items-start mb-4">
                <div class="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
                    <i class="fas fa-check-circle"></i>
                </div>
                <span class="text-xs font-medium bg-green-100 text-green-700 px-2 py-1 rounded flex items-center gap-1">
                    <i class="fas fa-arrow-up text-xs"></i> +5%
                </span>
            </div>
            <p class="text-sm text-gray-500 mb-1">% Cumplimiento</p>
            <p class="text-2xl font-bold text-gray-900">78%</p>
            <p class="text-xs text-gray-400 mt-1">Objetivos logrados vs planificados</p>
        </div>

        <div class="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <div class="flex justify-between items-start mb-4">
                <div class="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
                    <i class="fas fa-chart-line"></i>
                </div>
            </div>
            <p class="text-sm text-gray-500 mb-1">Índice de Eficiencia (IEA)</p>
            <p class="text-2xl font-bold text-gray-900">4.2 <span class="text-sm font-normal text-gray-400">/ 5.0</span></p>
            <div class="mt-3 flex gap-1">
                <div class="h-1.5 flex-1 bg-gray-800 rounded-full"></div>
                <div class="h-1.5 flex-1 bg-gray-800 rounded-full"></div>
                <div class="h-1.5 flex-1 bg-gray-800 rounded-full"></div>
                <div class="h-1.5 flex-1 bg-gray-800 rounded-full"></div>
                <div class="h-1.5 flex-1 bg-gray-200 rounded-full"></div>
            </div>
        </div>

        <div class="bg-white rounded-xl p-6 border-l-4 border-red-500 shadow-sm">
            <div class="flex justify-between items-start mb-4">
                <div class="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center text-red-600">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <span class="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">Críticas</span>
            </div>
            <p class="text-sm text-gray-500 mb-1">Alertas Activas</p>
            <p class="text-2xl font-bold text-red-600">12</p>
            <p class="text-xs text-gray-400 mt-1">Requieren atención inmediata</p>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div class="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Avance Financiero vs Impacto Pedagógico</h3>
                <button class="text-gray-400 hover:text-gray-600"><i class="fas fa-ellipsis-v"></i></button>
            </div>
            <div class="h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-dashed border-gray-200">
                <div class="text-center text-gray-400">
                    <i class="fas fa-chart-bar text-3xl mb-2"></i>
                    <p class="text-sm italic">Área de visualización del gráfico de dispersión</p>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div class="flex items-center gap-2 mb-4">
                <i class="fas fa-exclamation-circle text-red-500"></i>
                <h3 class="text-lg font-semibold text-gray-900">Alertas de Impacto Crítico</h3>
            </div>
            <p class="text-xs text-gray-500 mb-4">Alto gasto, bajo impacto SIGE</p>
            <div class="space-y-3">
                <div class="p-4 border border-gray-200 rounded-lg hover:shadow-md transition cursor-pointer">
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-medium text-sm text-gray-900">Taller de Nivelación Matemática 8vo Básico</h4>
                        <span class="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded font-medium">ALTO</span>
                    </div>
                    <p class="text-xs text-gray-500">Gasto: $4.5M</p>
                    <p class="text-xs text-gray-500">Impacto: 2/10</p>
                </div>
                <div class="p-4 border border-gray-200 rounded-lg hover:shadow-md transition cursor-pointer">
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-medium text-sm text-gray-900">Adquisición Tablets Laboratorio Ciencias</h4>
                        <span class="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded font-medium">MEDIO</span>
                    </div>
                    <p class="text-xs text-gray-500">Gasto: $12.0M</p>
                    <p class="text-xs text-gray-500">Impacto: 4/10</p>
                </div>
            </div>
            <a href="#" class="block text-center text-sm text-indigo-600 hover:text-indigo-800 mt-4 font-medium">Ver todas las alertas</a>
        </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-semibold text-gray-900">Seguimiento de Acciones PME</h3>
            <div class="flex gap-2">
                <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 flex items-center gap-2">
                    <i class="fas fa-filter"></i> Filtrar
                </button>
                <button class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 flex items-center gap-2">
                    <i class="fas fa-download"></i> Exportar
                </button>
            </div>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-gray-200 text-left text-gray-500">
                        <th class="pb-3 font-medium">Nombre de la Acción</th>
                        <th class="pb-3 font-medium">Dimensión</th>
                        <th class="pb-3 font-medium">Estado</th>
                        <th class="pb-3 font-medium">Presupuesto Usado</th>
                        <th class="pb-3 font-medium">Tendencia</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="border-b border-gray-100 hover:bg-gray-50">
                        <td class="py-4 font-medium text-gray-900">Capacitación Docente en Metodologías Activas</td>
                        <td class="py-4 text-gray-600">Gestión Pedagógica</td>
                        <td class="py-4"><span class="w-2.5 h-2.5 bg-green-500 rounded-full inline-block"></span></td>
                        <td class="py-4 text-gray-900">$3.200.000</td>
                        <td class="py-4 text-green-600"><i class="fas fa-arrow-up"></i></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

```

---

## `app/templates/ingesta/index.html`

```html
{% extends "layouts/base.html" %}

{% block title %}Ingesta de Datos - EduGest PME{% endblock %}

{% block content %}
<div class="p-8">
    <div class="mb-8">
        <h1 class="text-2xl font-bold text-indigo-700">Ingesta Manual de Datos</h1>
    </div>

    <div class="border-b border-gray-200 mb-6">
        <nav class="flex gap-6">
            <a href="#" class="pb-3 border-b-2 border-indigo-600 text-indigo-700 font-medium text-sm flex items-center gap-2">
                <i class="far fa-file-alt"></i> Registro Acciones PME (F-1)
            </a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm flex items-center gap-2">
                <i class="fas fa-th"></i> Datos App Ponderado (F-2)
            </a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm flex items-center gap-2">
                <i class="far fa-chart-bar"></i> Métricas SIGE (F-3)
            </a>
            <a href="#" class="pb-3 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm flex items-center gap-2">
                <i class="fas fa-users"></i> Asistencia Talleres (F-4)
            </a>
        </nav>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
            <h2 class="text-xl font-bold text-gray-900 mb-2">Carga Masiva</h2>
            <p class="text-sm text-gray-500 mb-6">Arrastre un archivo CSV o Excel estructurado para actualizar múltiples registros simultáneamente.</p>

            <div class="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-indigo-400 transition cursor-pointer bg-gray-50">
                <div class="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fas fa-cloud-upload-alt text-2xl text-indigo-600"></i>
                </div>
                <p class="text-indigo-700 font-medium mb-1">Cargar CSV/Excel</p>
                <p class="text-xs text-gray-500">Máx 10MB</p>
            </div>

            <div class="mt-8 pt-6 border-t border-gray-200">
                <div class="flex items-start gap-3">
                    <i class="fas fa-clock text-gray-400 mt-0.5"></i>
                    <div>
                        <p class="text-sm font-medium text-gray-900">Última Carga Exitosa</p>
                        <p class="text-sm text-gray-500">12 Oct 2025 - 14:30 hrs</p>
                        <a href="#" class="text-sm text-teal-600 hover:text-teal-800 font-medium mt-1 inline-block">Ver historial de cargas</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
            <div class="flex justify-between items-center mb-6">
                <h2 class="text-xl font-bold text-gray-900">Ingesta Manual (F-1)</h2>
                <span class="flex items-center gap-2 text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full">
                    <span class="w-2 h-2 bg-indigo-600 rounded-full"></span> Modo Edición
                </span>
            </div>

            <form class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Nombre de la Acción</label>
                    <input type="text" placeholder="Ej: Taller de Convivencia Escolar" 
                           class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Dimensión PME</label>
                        <div class="relative">
                            <select class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm appearance-none bg-white">
                                <option>Seleccione dimensión</option>
                                <option>Gestión Pedagógica</option>
                                <option>Liderazgo Escolar</option>
                                <option>Convivencia Escolar</option>
                                <option>Gestión de Recursos</option>
                            </select>
                            <i class="fas fa-chevron-down absolute right-3 top-3 text-gray-400 text-xs pointer-events-none"></i>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Sub-dimensión</label>
                        <div class="relative">
                            <select class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm appearance-none bg-white">
                                <option>Seleccione sub-dimensión</option>
                            </select>
                            <i class="fas fa-chevron-down absolute right-3 top-3 text-gray-400 text-xs pointer-events-none"></i>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Responsable</label>
                        <div class="relative">
                            <i class="fas fa-user absolute left-3 top-3 text-gray-400 text-sm"></i>
                            <input type="text" placeholder="Buscar docente/directivo..." 
                                   class="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm">
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Estado Actual</label>
                        <div class="relative">
                            <select class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm appearance-none bg-white">
                                <option>Planificada</option>
                                <option>En Ejecución</option>
                                <option>Finalizada</option>
                                <option>Cancelada</option>
                            </select>
                            <i class="fas fa-chevron-down absolute right-3 top-3 text-gray-400 text-xs pointer-events-none"></i>
                        </div>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Descripción / Notas Adicionales</label>
                    <textarea rows="4" placeholder="Detalles de la implementación o desviaciones..." 
                              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm resize-none"></textarea>
                </div>

                <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
                    <button type="button" class="px-6 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition">Cancelar</button>
                    <button type="button" class="px-6 py-2.5 border border-indigo-200 rounded-lg text-sm text-indigo-700 hover:bg-indigo-50 transition flex items-center gap-2">
                        <i class="fas fa-sync-alt"></i> Sincronizar Ahora
                    </button>
                    <button type="submit" class="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition flex items-center gap-2">
                        <i class="fas fa-save"></i> Guardar Cambios
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

```

---

## `app/templates/reportes/index.html`

```html
{% extends "layouts/base.html" %}

{% block title %}Reportes - EduGest PME{% endblock %}

{% block content %}
<div class="p-8">
    <!-- Header -->
    <div class="flex justify-between items-start mb-2">
        <div>
            <h1 class="text-2xl font-bold text-gray-900">Módulo de Reportes</h1>
        </div>
        <div class="relative">
            <i class="fas fa-search absolute left-3 top-3 text-gray-400 text-sm"></i>
            <input type="text" placeholder="Buscar reportes..." class="pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none w-64">
        </div>
    </div>

    <div class="mb-8">
        <h2 class="text-3xl font-bold text-gray-900 mb-2">Generador de Reportes e Informes PME</h2>
        <p class="text-gray-500">Gestione, descargue y personalice la documentación oficial del Plan de Mejoramiento Educativo.</p>
    </div>

    <!-- Descarga Rápida -->
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Descarga Rápida</h3>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <!-- Reporte Ejecutivo -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-20 h-20 bg-red-50 rounded-bl-full"></div>
            <div class="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center text-white mb-4">
                <i class="fas fa-file-pdf text-xl"></i>
            </div>
            <h4 class="text-lg font-bold text-gray-900 mb-2">Reporte Ejecutivo Sostenedor</h4>
            <p class="text-sm text-gray-500 mb-6 leading-relaxed">Resumen directivo del avance de metas y presupuesto ejecutado para presentación al sostenedor.</p>
            <a href="#" class="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-2">
                <i class="fas fa-download"></i> Descargar PDF
            </a>
        </div>

        <!-- Matriz de Rendición -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-20 h-20 bg-indigo-50 rounded-bl-full"></div>
            <div class="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center text-white mb-4">
                <i class="fas fa-table text-xl"></i>
            </div>
            <h4 class="text-lg font-bold text-gray-900 mb-2">Matriz de Rendición</h4>
            <p class="text-sm text-gray-500 mb-6 leading-relaxed">Sabana de datos detallada de gastos y acciones vinculadas para control financiero.</p>
            <a href="#" class="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-2">
                <i class="fas fa-download"></i> Descargar Excel
            </a>
        </div>

        <!-- Informe Auditoría -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-20 h-20 bg-gray-100 rounded-bl-full"></div>
            <div class="w-12 h-12 bg-gray-600 rounded-lg flex items-center justify-center text-white mb-4">
                <i class="fas fa-file-archive text-xl"></i>
            </div>
            <h4 class="text-lg font-bold text-gray-900 mb-2">Informe Auditoría MINEDUC</h4>
            <p class="text-sm text-gray-500 mb-6 leading-relaxed">Formato oficial requerido por la Superintendencia de Educación con todos los verificadores.</p>
            <a href="#" class="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-2">
                <i class="fas fa-download"></i> Descargar ZIP
            </a>
        </div>
    </div>

    <!-- Configuración de Reporte Personalizado -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="p-6 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900 mb-1">Configuración de Reporte Personalizado</h3>
            <p class="text-sm text-gray-500">Defina los parámetros específicos para generar un informe a medida.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 p-6">
            <!-- Formulario -->
            <div class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Periodo de Ejecución</label>
                    <div class="flex gap-3">
                        <div class="relative flex-1">
                            <i class="far fa-calendar absolute left-3 top-3 text-gray-400 text-sm"></i>
                            <input type="text" value="01/03/2024" class="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                        </div>
                        <div class="relative flex-1">
                            <i class="far fa-calendar absolute left-3 top-3 text-gray-400 text-sm"></i>
                            <input type="text" value="31/12/2024" class="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                        </div>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-3">Dimensiones PME (Seleccione al menos una)</label>
                    <div class="space-y-2">
                        <label class="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" checked class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500">
                            <span class="text-sm text-gray-700">Gestión Pedagógica</span>
                        </label>
                        <label class="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" checked class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500">
                            <span class="text-sm text-gray-700">Liderazgo Escolar</span>
                        </label>
                        <label class="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500">
                            <span class="text-sm text-gray-700">Convivencia Escolar</span>
                        </label>
                        <label class="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500">
                            <span class="text-sm text-gray-700">Gestión de Recursos</span>
                        </label>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Niveles / Cursos Asociados</label>
                    <div class="relative">
                        <select class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm appearance-none bg-white focus:ring-2 focus:ring-indigo-500 outline-none">
                            <option>Todos los niveles (Institucional)</option>
                        </select>
                        <i class="fas fa-chevron-down absolute right-3 top-3 text-gray-400 text-xs pointer-events-none"></i>
                    </div>
                </div>

                <div class="flex items-center justify-between">
                    <label class="text-sm text-gray-700">Incluir Medios de Verificación (Anexos)</label>
                    <div class="relative inline-block w-11 h-6 bg-gray-200 rounded-full cursor-pointer">
                        <span class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow"></span>
                    </div>
                </div>
            </div>

            <!-- Preview -->
            <div class="flex items-center justify-center">
                <div class="w-full max-w-sm bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                    <div class="bg-teal-700 text-white p-4 flex justify-between items-center">
                        <div>
                            <p class="text-sm font-medium">Colegio San Juan de la Montaña</p>
                            <p class="text-xs text-teal-200">RBD: 12345-6</p>
                        </div>
                        <i class="fas fa-envelope text-teal-200"></i>
                    </div>
                    <div class="p-6 text-center">
                        <h4 class="text-lg font-bold text-gray-900 mb-1">Reporte de Avance PME 2024</h4>
                        <p class="text-xs text-gray-500 mb-6">Periodo: Mar 2024 - Dic 2024</p>

                        <div class="space-y-3 mb-6">
                            <div class="h-3 bg-gray-100 rounded-full w-3/4 mx-auto"></div>
                            <div class="h-3 bg-gray-100 rounded-full w-full mx-auto"></div>
                            <div class="h-3 bg-gray-100 rounded-full w-5/6 mx-auto"></div>
                        </div>

                        <div class="text-left">
                            <p class="text-xs font-medium text-gray-700 mb-2">Avance Gestión Pedagógica</p>
                            <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div class="h-full bg-indigo-600 rounded-full" style="width: 65%"></div>
                            </div>
                            <div class="flex justify-between text-xs text-gray-500 mt-1">
                                <span>Ejecutado: 65%</span>
                                <span>Meta: 100%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

---

## `requirements.txt`

```text
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
Werkzeug==3.0.3
pandas==2.2.2
numpy==1.26.4
python-dotenv==1.0.1
Faker==25.8.0

```

---

## `seed.py`

```python
#!/usr/bin/env python3
"""Script independiente para poblar la base de datos con datos pseudo-reales.

Ejecutar desde la raíz del proyecto:
    python seed.py
"""
import sys
import os

# Agrega la raíz del proyecto al PYTHONPATH para poder importar `app`
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import random
from datetime import date, datetime
from faker import Faker

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.pme import (
    Establecimiento,
    DimensionPME,
    ObjetivoPME,
    AccionPME,
    Curso,
)
from app.models.metrics import (
    Estudiante,
    RegistroAppPonderado,
    MetricaSIGE,
    ParticipacionAccion,
    IndicadorAccion,
)
from app.services.pme_engine import (
    calcular_iea,
    calcular_correlacion_pearson,
    determinar_semaforo,
    proyectar_cumplimiento,
)

fake = Faker("es_CL")
app = create_app("development")

# =============================================================================
# CONFIGURACIÓN DE SEMILLA
# =============================================================================
NUM_ESTUDIANTES_POR_CURSO = 15  # 15 x 4 cursos = 60 estudiantes
NUM_MESES_REGISTRO = 8          # Marzo a Octubre
ANIO_GESTION = 2026

DIMENSIONES = [
    ("Gestión Pedagógica", "GP", "Acciones orientadas al mejoramiento del aprendizaje."),
    ("Liderazgo Escolar", "LE", "Fortalecimiento de la gestión directiva."),
    ("Convivencia Escolar", "CE", "Promoción de un clima positivo de convivencia."),
    ("Gestión de Recursos", "GR", "Optimización del uso de recursos SEP/PIE."),
]

ACCIONES_DATA = [
    # (nombre, dim_index, presupuesto, estado, responsable, curso_objetivo, meta_cuantitativa)
    ("Taller de Refuerzo Matemático", 0, 2500000, "En Ejecución", "Prof. Marta Díaz", "8° Básico", "+0.8 pts promedio matemáticas"),
    ("Lectura Comprensiva Diaria", 0, 1200000, "En Ejecución", "Prof. Carlos Vega", "5° Básico", "+5% comprensión lectora"),
    ("Capacitación Docente en Metodologías Activas", 0, 3200000, "Finalizada", "UTP Ana Ríos", "Todos", "90% implementación"),
    ("Programa de Liderazgo Estudiantil", 1, 1800000, "En Ejecución", "Directora Pía Soto", "7° Básico", "20 líderes capacitados"),
    ("Talleres de Gestión Emocional para Directivos", 1, 1500000, "Planificada", "Consultora Externa", "Directivos", "100% asistencia directiva"),
    ("Mediación de Conflictos entre Pares", 2, 900000, "En Ejecución", "Orientadora Luz Mora", "6° Básico", "-10% conflictos graves"),
    ("Campaña de Convivencia Escolar Positiva", 2, 1100000, "En Ejecución", "CEP Juan Pérez", "Todos", "80% percepción positiva"),
    ("Adquisición Tablets Laboratorio Ciencias", 3, 12000000, "En Ejecución", "Admin Roberto Fuentes", "8° Básico", "100% cobertura lab ciencias"),
    ("Mantención Infraestructura Deportiva", 3, 4500000, "Planificada", "Admin Roberto Fuentes", "Todos", "0 riesgos estructurales"),
    ("Reforzamiento Habilidades Socioemocionales", 2, 2000000, "En Ejecución", "Orientadora Luz Mora", "5° Básico", "+0.5 autoevaluación socioemocional"),
]


def crear_establecimiento():
    """Crea el establecimiento de prueba."""
    est = Establecimiento(
        nombre="Liceo de Excelencia",
        rbd="78332482-2",
        direccion="Av. Libertador Bernardo O'Higgins 1234, Santiago",
        telefono="+56 2 2123 4567",
        email_institucional="contacto@liceodeexcelencia.edu.cl",
        logo_url=None,
        activo=True,
    )
    db.session.add(est)
    db.session.commit()
    return est


def crear_usuario_admin(establecimiento_id):
    """Crea el usuario administrador/director de prueba."""
    admin = User(
        email="admin@liceo.cl",
        nombre="Director de Prueba",
        rol=User.ROL_DIRECTOR,
        activo=True,
        establecimiento_id=establecimiento_id,
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    return admin


def crear_dimensiones():
    """Crea las 4 dimensiones PME oficiales."""
    dims = []
    for nombre, codigo, desc in DIMENSIONES:
        d = DimensionPME(nombre=nombre, codigo=codigo, descripcion=desc, orden=len(dims))
        db.session.add(d)
        dims.append(d)
    db.session.commit()
    return dims


def crear_objetivos(dimensiones):
    """Crea 2 objetivos por dimensión."""
    objetivos = []
    for dim in dimensiones:
        for i in range(1, 3):
            obj = ObjetivoPME(
                dimension_id=dim.id,
                nombre=f"Objetivo {i}: {fake.sentence(nb_words=6)}",
                descripcion=fake.paragraph(nb_sentences=2),
                anio=ANIO_GESTION,
                estado="Activo",
            )
            db.session.add(obj)
            objetivos.append(obj)
    db.session.commit()
    return objetivos


def crear_acciones(objetivos):
    """Crea 10 acciones PME distribuidas en los objetivos."""
    acciones = []
    for idx, (nombre, dim_idx, presupuesto, estado, responsable, curso, meta) in enumerate(ACCIONES_DATA):
        objetivos_dim = [o for o in objetivos if o.dimension_id == dim_idx + 1]
        objetivo = random.choice(objetivos_dim) if objetivos_dim else random.choice(objetivos)

        inicio = date(ANIO_GESTION, 3, 1) if estado != "Planificada" else date(ANIO_GESTION, 8, 1)
        fin = date(ANIO_GESTION, 11, 30)

        if estado == "Finalizada":
            ejecutado = presupuesto * random.uniform(0.95, 1.05)
        elif estado == "En Ejecución":
            ejecutado = presupuesto * random.uniform(0.40, 0.75)
        else:
            ejecutado = 0.0

        acc = AccionPME(
            objetivo_id=objetivo.id,
            nombre=nombre,
            descripcion=fake.paragraph(nb_sentences=3),
            presupuesto_asignado=presupuesto,
            presupuesto_ejecutado=round(ejecutado, 0),
            estado=estado,
            responsable=responsable,
            fecha_inicio=inicio,
            fecha_fin=fin,
            meta_cualitativa=fake.sentence(nb_words=8),
            meta_cuantitativa=meta,
            indicador_medible=meta.split("+")[-1] if "+" in meta else meta,
            curso_objetivo=curso,
        )
        db.session.add(acc)
        acciones.append(acc)
    db.session.commit()
    return acciones


def crear_cursos(establecimiento_id):
    """Crea los 4 cursos de prueba (5° a 8° Básico)."""
    cursos = []
    for nivel in range(5, 9):
        c = Curso(
            nombre=f"{nivel}° Básico",
            nivel=f"{nivel}° Básico",
            anio=ANIO_GESTION,
            establecimiento_id=establecimiento_id,
        )
        db.session.add(c)
        cursos.append(c)
    db.session.commit()
    return cursos


def crear_estudiantes(cursos, establecimiento_id):
    """Crea estudiantes pseudo-reales distribuidos en los cursos."""
    estudiantes = []
    for curso in cursos:
        for _ in range(NUM_ESTUDIANTES_POR_CURSO):
            e = Estudiante(
                nombre=fake.first_name(),
                apellido=fake.last_name(),
                matricula=f"MAT-{ANIO_GESTION}-{fake.unique.random_int(min=1000, max=9999)}",
                curso_id=curso.id,
                establecimiento_id=establecimiento_id,
                activo=True,
            )
            db.session.add(e)
            estudiantes.append(e)
    db.session.commit()
    return estudiantes


def crear_registros_app_ponderado(estudiantes):
    """Genera registros mensuales de notas y asistencia (200+ registros)."""
    asignaturas = ["Matemáticas", "Lenguaje", "Ciencias", "Historia", "Inglés"]
    meses = [f"{ANIO_GESTION}-{m:02d}" for m in range(3, 11)]

    registros_totales = 0
    for estudiante in estudiantes:
        nota_base = random.uniform(3.5, 6.0)
        asist_base = random.uniform(75.0, 98.0)

        for periodo in meses:
            for asig in asignaturas:
                mejora = random.uniform(-0.2, 0.3)
                nota = min(7.0, max(1.0, nota_base + mejora + random.gauss(0, 0.3)))
                asist = min(100.0, max(50.0, asist_base + random.gauss(0, 3)))

                reg = RegistroAppPonderado(
                    estudiante_id=estudiante.id,
                    periodo=periodo,
                    asignatura=asig,
                    promedio_notas=round(nota, 2),
                    porcentaje_asistencia=round(asist, 1),
                    bitacora=fake.sentence(nb_words=10) if random.random() > 0.7 else None,
                )
                db.session.add(reg)
                registros_totales += 1

    db.session.commit()
    print(f"  → {registros_totales} registros App Ponderado creados.")


def crear_participaciones(estudiantes, acciones):
    """Genera participaciones de estudiantes en acciones PME."""
    acciones_con_participantes = [a for a in acciones if a.curso_objetivo != "Todos" and a.estado != "Planificada"]

    for accion in acciones_con_participantes:
        estudiantes_curso = [e for e in estudiantes if e.curso.nombre == accion.curso_objetivo]
        if not estudiantes_curso:
            continue

        for est in estudiantes_curso:
            if random.random() > 0.25:
                horas = random.uniform(4, 20)
                talleres = int(horas / 2)
                part = ParticipacionAccion(
                    estudiante_id=est.id,
                    accion_id=accion.id,
                    horas_asistencia=round(horas, 1),
                    asistencia_talleres=talleres,
                )
                db.session.add(part)
    db.session.commit()


def crear_metricas_sige(establecimiento_id):
    """Genera métricas SIGE mensuales consolidadas."""
    for mes in range(3, 11):
        matricula = 240 + random.randint(-5, 5)
        asist = random.uniform(88.0, 94.5)
        calif = random.uniform(4.8, 5.4)

        m = MetricaSIGE(
            establecimiento_id=establecimiento_id,
            anio=ANIO_GESTION,
            mes=mes,
            matricula_oficial=matricula,
            asistencia_oficial_validada=round(asist, 2),
            calificaciones_consolidadas=round(calif, 2),
            observaciones=fake.sentence(nb_words=6) if random.random() > 0.5 else None,
        )
        db.session.add(m)
    db.session.commit()


def crear_indicadores(acciones):
    """Calcula y almacena indicadores mensuales (IEA, Pearson, Semáforo)."""
    meses = [f"{ANIO_GESTION}-{m:02d}" for m in range(3, 11)]

    for accion in acciones:
        parts = ParticipacionAccion.query.filter_by(accion_id=accion.id).all()
        if not parts:
            continue

        horas_list = []
        notas_delta_list = []

        for p in parts:
            regs = RegistroAppPonderado.query.filter_by(estudiante_id=p.estudiante_id).order_by(RegistroAppPonderado.periodo).all()
            if len(regs) >= 2:
                nota_inicial = regs[0].promedio_notas
                nota_final = regs[-1].promedio_notas
                horas_list.append(p.horas_asistencia)
                notas_delta_list.append(nota_final - nota_inicial)

        r_pearson, _ = calcular_correlacion_pearson(horas_list, notas_delta_list)
        gastos_mensuales = []

        for i, mes in enumerate(meses):
            gasto = (accion.presupuesto_ejecutado / len(meses)) * random.uniform(0.8, 1.2)
            gastos_mensuales.append(gasto)

            delta_rend = random.uniform(0.1, 0.8) if r_pearson and r_pearson > 0.3 else random.uniform(0.0, 0.3)
            delta_asist = random.uniform(1, 5)
            iea_val = calcular_iea(gasto, 10, delta_rend, delta_asist)

            acumulado = sum(gastos_mensuales)
            proy = proyectar_cumplimiento(
                [acumulado / accion.presupuesto_asignado],
                1.0
            ) if accion.presupuesto_asignado > 0 else 0.0

            semaforo = determinar_semaforo(proy)

            ind = IndicadorAccion(
                accion_id=accion.id,
                mes=mes,
                iea=iea_val,
                correlacion_pearson=r_pearson,
                estado_semaforo=semaforo,
                proyeccion_cumplimiento=proy,
                gasto_mes=round(gasto, 0),
            )
            db.session.add(ind)

    db.session.commit()


def main():
    """Ejecuta la población completa de la base de datos."""
    with app.app_context():
        print("=" * 60)
        print("  SEED EDUGEST PME - Población de Datos Pseudo-Reales")
        print("=" * 60)

        db.create_all()

        print("\n[1/8] Creando establecimiento...")
        est = crear_establecimiento()

        print("[2/8] Creando usuario admin (admin@liceo.cl / admin123)...")
        crear_usuario_admin(est.id)

        print("[3/8] Creando dimensiones PME...")
        dims = crear_dimensiones()

        print("[4/8] Creando objetivos...")
        objs = crear_objetivos(dims)

        print("[5/8] Creando acciones PME...")
        accs = crear_acciones(objs)

        print("[6/8] Creando cursos y estudiantes...")
        cursos = crear_cursos(est.id)
        ests = crear_estudiantes(cursos, est.id)

        print("[7/8] Creando registros App Ponderado + Participaciones + SIGE...")
        crear_registros_app_ponderado(ests)
        crear_participaciones(ests, accs)
        crear_metricas_sige(est.id)

        print("[8/8] Calculando indicadores (IEA, Pearson, Semáforo)...")
        crear_indicadores(accs)

        print("\n" + "=" * 60)
        print("  ✅ Base de datos poblada exitosamente.")
        print(f"  • Establecimiento: {est.nombre} (RBD: {est.rbd})")
        print(f"  • Usuarios: 1 (admin@liceo.cl / admin123)")
        print(f"  • Cursos: {len(cursos)}")
        print(f"  • Estudiantes: {len(ests)}")
        print(f"  • Acciones PME: {len(accs)}")
        print(f"  • Indicadores calculados por mes para cada acción.")
        print("=" * 60)


if __name__ == "__main__":
    main()

```

---


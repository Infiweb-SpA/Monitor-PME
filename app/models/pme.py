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
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
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
# 02 - Modelos de Datos (SQLAlchemy)

## Diagrama Entidad-Relación

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Establecimiento│◄────┤     Curso        │◄────┤   Estudiante    │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)          │     │ id (PK)         │
│ nombre          │     │ nombre           │     │ nombre          │
│ rbd (unique)    │     │ nivel            │     │ apellido        │
│ direccion       │     │ anio             │     │ matricula (UQ)  │
│ telefono        │     │ establecimiento_id│    │ curso_id (FK)   │
│ email_instituc  │     └──────────────────┘     │ establecimiento_id│
│ logo_url        │                              │ activo          │
│ activo          │                              └────────┬────────┘
└────────┬────────┘                                       │
         │                                                │
         │         ┌──────────────────────────────────────┘
         │         │
         │    ┌────┴──────────────┐     ┌─────────────────────────┐
         │    │ RegistroAppPond   │     │   ParticipacionAccion   │
         │    ├───────────────────┤     ├─────────────────────────┤
         │    │ id (PK)           │     │ id (PK)                 │
         │    │ estudiante_id(FK) │     │ estudiante_id (FK)      │
         │    │ periodo (idx)     │     │ accion_id (FK)          │
         │    │ asignatura        │     │ horas_asistencia        │
         │    │ promedio_notas    │     │ asistencia_talleres     │
         │    │ %_asistencia      │     └─────────────────────────┘
         │    │ bitacora          │
         │    └───────────────────┘
         │
         │    ┌───────────────────┐
         └───►│   MetricaSIGE     │
              ├───────────────────┤
              │ id (PK)           │
              │ establecimiento_id│
              │ anio, mes          │
              │ matricula_oficial │
              │ asistencia_oficial│
              │ calif_consolidadas│
              └───────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  DimensionPME   │◄────┤  ObjetivoPME     │◄────┤   AccionPME     │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)          │     │ id (PK)         │
│ nombre (UQ)     │     │ dimension_id(FK) │     │ objetivo_id(FK) │
│ codigo (UQ)     │     │ nombre           │     │ nombre          │
│ descripcion     │     │ descripcion      │     │ descripcion     │
│ orden           │     │ anio             │     │ presup_asignado │
└─────────────────┘     │ estado           │     │ presup_ejecutado│
                        └──────────────────┘     │ estado          │
                                                  │ responsable     │
                                                  │ fecha_inicio    │
                                                  │ fecha_fin       │
                                                  │ meta_cualitativa│
                                                  │ meta_cuantitativa│
                                                  │ indicador_medible│
                                                  │ curso_objetivo  │
                                                  └────────┬────────┘
                                                           │
                              ┌────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │           IndicadorAccion               │
         ├─────────────────────────────────────────┤
         │ id (PK)                                 │
         │ accion_id (FK)                          │
         │ mes (formato "2026-03")                 │
         │ iea (float)                             │
         │ correlacion_pearson (float)             │
         │ estado_semaforo (Rojo/Amarillo/Verde)   │
         │ proyeccion_cumplimiento (0.0-1.0+)      │
         │ gasto_mes (float)                       │
         └─────────────────────────────────────────┘

┌─────────────────┐
│      User       │
├─────────────────┤
│ id (PK)         │
│ email (UQ, idx) │
│ password_hash   │
│ nombre          │
│ rol             │
│ activo          │
│ establecimiento_id (FK, nullable) │
└─────────────────┘
```

## Descripción detallada de cada modelo

### `app/models/user.py`

**User** — Hereda de `UserMixin` (Flask-Login) y `db.Model`.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | Integer | PK |
| email | String(120) | unique, nullable=False, index |
| password_hash | String(256) | nullable=False |
| nombre | String(100) | nullable=False |
| rol | String(50) | default="Encargado PME" |
| activo | Boolean | default=True |
| establecimiento_id | Integer | FK → establecimientos.id, nullable |

**Roles definidos como constantes de clase:**
- `ROL_DIRECTOR = "Director"`
- `ROL_UTP = "UTP"`
- `ROL_ENCARGADO_PME = "Encargado PME"`
- `ROL_SOSTENEDOR = "Sostenedor"`
- `ROL_ADMIN = "Administrador"`

**Métodos:**
- `set_password(password)` → hashea con Werkzeug
- `check_password(password)` → verifica hash
- `es_admin()` → True si rol es Admin o Director
- `es_sostenedor()` → True si rol es Sostenedor

**Decorador crítico:**
```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

---

### `app/models/pme.py`

**Establecimiento**
| Campo | Notas |
|-------|-------|
| id | PK |
| nombre | String(150) |
| rbd | String(20), unique, index |
| direccion, telefono, email_institucional, logo_url | Opcionales |
| activo | default=True |

**Relaciones:** `usuarios`, `cursos`, `metricas_sige`, `estudiantes` (all lazy="dynamic")

**DimensionPME** — Las 4 dimensiones oficiales del PME chileno
| Campo | Notas |
|-------|-------|
| id | PK |
| nombre | String(100), unique |
| codigo | String(20), unique |
| descripcion | Text |
| orden | Integer, default=0 |

**Constantes de clase:**
- `GESTION_PEDAGOGICA = "Gestión Pedagógica"`
- `LIDERAZGO_ESCOLAR = "Liderazgo Escolar"`
- `CONVIVENCIA_ESCOLAR = "Convivencia Escolar"`
- `GESTION_RECURSOS = "Gestión de Recursos"`

**ObjetivoPME**
| Campo | Notas |
|-------|-------|
| id | PK |
| dimension_id | FK → dimensiones_pme.id |
| nombre | String(200) |
| descripcion | Text |
| anio | Integer, default=2026 |
| estado | String(30), default="Activo" |

**AccionPME**
| Campo | Notas |
|-------|-------|
| id | PK |
| objetivo_id | FK → objetivos_pme.id |
| nombre | String(200) |
| descripcion | Text |
| presupuesto_asignado | Float, default=0.0 |
| presupuesto_ejecutado | Float, default=0.0 |
| estado | String(30), default="Planificada" |
| responsable | String(100) |
| fecha_inicio, fecha_fin | Date, nullable |
| meta_cualitativa | Text |
| meta_cuantitativa | String(100) |
| indicador_medible | String(100) |
| curso_objetivo | String(50) |

**Método:** `porcentaje_ejecucion_presupuesto()` → calcula % ejecutado/asignado

**Relaciones:** `participaciones` (ParticipacionAccion), `indicadores` (IndicadorAccion)

**Curso**
| Campo | Notas |
|-------|-------|
| id | PK |
| nombre | String(50) |
| nivel | String(50) |
| anio | Integer, default=2026 |
| establecimiento_id | FK → establecimientos.id |

---

### `app/models/metrics.py`

**Estudiante**
| Campo | Notas |
|-------|-------|
| id | PK |
| nombre, apellido | String(100) |
| matricula | String(30), unique, index |
| curso_id | FK → cursos.id |
| establecimiento_id | FK → establecimientos.id |
| activo | Boolean, default=True |

**Property:** `nombre_completo` → `"{nombre} {apellido}"`

**Relaciones:** `registros_app`, `participaciones`

**RegistroAppPonderado** (Formulario F-2)
| Campo | Notas |
|-------|-------|
| id | PK |
| estudiante_id | FK → estudiantes.id |
| periodo | String(10), formato "2026-03", index |
| asignatura | String(50) |
| promedio_notas | Float (escala 1.0 - 7.0) |
| porcentaje_asistencia | Float |
| bitacora | Text (opcional) |

**MetricaSIGE** (Formulario F-3)
| Campo | Notas |
|-------|-------|
| id | PK |
| establecimiento_id | FK → establecimientos.id |
| anio | Integer |
| mes | Integer |
| matricula_oficial | Integer |
| asistencia_oficial_validada | Float |
| calificaciones_consolidadas | Float, nullable |
| observaciones | Text, nullable |

**ParticipacionAccion** (Formulario F-4)
| Campo | Notas |
|-------|-------|
| id | PK |
| estudiante_id | FK → estudiantes.id |
| accion_id | FK → acciones_pme.id |
| horas_asistencia | Float, default=0.0 |
| asistencia_talleres | Integer, default=0 |

**IndicadorAccion** — Resultados del motor algorítmico
| Campo | Notas |
|-------|-------|
| id | PK |
| accion_id | FK → acciones_pme.id |
| mes | String(10), formato "2026-03" |
| iea | Float (0.0 - 5.0) |
| correlacion_pearson | Float (-1.0 a 1.0) |
| estado_semaforo | String(20): "Rojo", "Amarillo", "Verde" |
| proyeccion_cumplimiento | Float (0.0 - 1.0+) |
| gasto_mes | Float, default=0.0 |

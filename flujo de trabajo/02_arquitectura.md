# Arquitectura del Sistema — EduGest PME

## 1. Visión general

EduGest PME es una aplicación **Flask** monolítica con arquitectura **MVC** (Modelo–Vista–Controlador) organizada en *blueprints*. Usa **SQLAlchemy** sobre **SQLite** para persistencia, **Jinja2** para las vistas y **Tailwind CSS + FontAwesome** (vía CDN) para la interfaz.

```
run.py
  └── app/__init__.py  (create_app)
        ├── app/config.py          ← Configuración por entorno
        ├── app/extensions.py      ← db + login_manager (evita imports circulares)
        ├── app/models/            ← Modelos SQLAlchemy
        ├── app/routes/            ← Blueprints (controladores HTTP)
        ├── app/services/          ← Lógica de negocio / algoritmos
        └── app/templates/         ← Vistas Jinja2
```

---

## 2. Punto de entrada y arranque

### `run.py`
- Importa `create_app` desde `app/__init__.py`.
- Crea la app con el entorno indicado por `FLASK_ENV` (por defecto `development`).
- Ejecuta el servidor en `0.0.0.0:5000` con `debug=True`.

### `app/__init__.py` — Application Factory
1. Crea la instancia `Flask` con `templates/` y `static/`.
2. Carga la clase de configuración desde `app/config.py` según el entorno.
3. Inicializa extensiones: `db` (Flask-SQLAlchemy) y `login_manager` (Flask-Login).
4. Registra los blueprints (ver sección 4).
5. Dentro del contexto de app, **importa todos los modelos** y ejecuta `db.create_all()`. Esto garantiza que SQLAlchemy reconozca todas las tablas al crear la base.
6. Registra el filtro Jinja `from_json`.
7. Ruta raíz `/` redirige a `auth.login`.

> ⚠️ **Dependencia crítica:** los modelos deben importarse dentro de `create_app()` antes de `db.create_all()`. Si se añade un modelo nuevo y no se importa aquí, su tabla no se creará.

---

## 3. Configuración (`app/config.py`)

| Clase | Entorno | Características |
|---|---|---|
| `Config` | Base | `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (`sqlite:///edugest_pme.db`), `UPLOAD_FOLDER`, límites de archivo y umbrales del semáforo por defecto. |
| `DevelopmentConfig` | `development` | `DEBUG=True`, `SQLALCHEMY_ECHO=True` (imprime cada SQL en consola). |
| `ProductionConfig` | `production` | `DEBUG=False`. |
| `TestingConfig` | `testing` | SQLite en memoria, `TESTING=True`. |

`config_por_entorno` mapea los nombres usados por `create_app`.

> 📌 La base de datos física vive en `instance/edugest_pme.db`.

---

## 4. Blueprints y sus dependencias

Registrados en `app/__init__.py::_registrar_blueprints`:

| Blueprint | Prefijo | Archivo | Depende de |
|---|---|---|---|
| `auth_bp` | `/auth` | `app/routes/auth.py` | `User` (`models/user.py`), Flask-Login |
| `dashboard_bp` | `/dashboard` | `app/routes/dashboard.py` | `AccionPME`, `DimensionPME`, `IndicadorAccion`, `DefinicionIndicador`, NumPy |
| `ingesta_bp` | `/ingesta` | `app/routes/ingesta.py` | `AccionPME`, `RegistroAppPonderado`, `MetricaSIGE`, `ParticipacionAccion`, `Estudiante`, `DefinicionIndicador`, `MedicionIndicador`, `pme_engine` |
| `acciones_bp` | `/acciones` | `app/routes/acciones.py` | `AccionPME`, `ObjetivoPME`, `DefinicionIndicador`, `pme_engine` (impacto individual), pandas/openpyxl, `utils.parse_date` |
| `reportes_bp` | `/reportes` | `app/routes/reportes.py` | Todos los modelos PME + métricas, pandas/openpyxl, zipfile |
| `config_bp` | `/configuracion` | `app/routes/config.py` | `Establecimiento`, `ConfiguracionSistema`, `User` |

### Flujo de una petición

```
Navegador
  → blueprint (routes/*.py)
    → consulta/escritura de modelos (models/*.py + extensions.db)
    → lógica de cálculo (services/pme_engine.py)
  → render_template ("templates/...")  ó  jsonify(...)
Navegador ← HTML / JSON
```

---

## 5. Modelos y relaciones

### `app/models/user.py`
- `User` → login, roles, contraseña hasheada, FK a `Establecimiento`.

### `app/models/pme.py` (jerarquía PME)
```
Establecimiento
  ├── Curso
  │     └── Estudiante
  ├── MetricaSIGE
  └── ConfiguracionSistema
DimensionPME
  └── ObjetivoPME
        └── AccionPME
              ├── ParticipacionAccion
              ├── IndicadorAccion          (resultados calculados)
              └── DefinicionIndicador      (indicadores definidos en F-1)
                    └── MedicionIndicador  (valores medidos en F-2 parte 2)
```

- `AccionPME` conserva campos **legacy** (`indicador_tipo`, `linea_base_valor`, `meta_valor`, etc.) para compatibilidad con el flujo antiguo del motor.
- `AccionPME` se relaciona con `DefinicionIndicador` y `IndicadorAccion`.

### `app/models/metrics.py`
| Modelo | Tabla | Propósito | FK principales |
|---|---|---|---|
| `Estudiante` | `estudiantes` | Alumnos | `curso_id`, `establecimiento_id` |
| `RegistroAppPonderado` | `registros_app_ponderado` | Notas y asistencia (F-2) | `estudiante_id` |
| `MetricaSIGE` | `metricas_sige` | Métricas oficiales (F-3) | `establecimiento_id` |
| `ParticipacionAccion` | `participaciones_accion` | Horas/asistencia a talleres (F-4) | `estudiante_id`, `accion_id`, `periodo` |
| `DefinicionIndicador` | `definiciones_indicador` | Indicadores personalizados (F-1) | `accion_id` |
| `MedicionIndicador` | `mediciones_indicador` | Valores medidos (F-2 parte 2) | `indicador_def_id`, `estudiante_id` |
| `IndicadorAccion` | `indicadores_accion` | Resultados del motor por mes (IEA, IPA, Pearson, semáforo, proyección) | `accion_id` |

> ⚠️ `DefinicionIndicador.asignatura` es **opcional** (`nullable=True`). Si es `NULL`, se interpreta como *Transversal* en la UI.
> ⚠️ `RegistroAppPonderado` **no** tiene FK a `AccionPME` ni a `DefinicionIndicador`; el vínculo con el taller se hace por **estudiante + periodo + asignatura**.

---

## 6. Servicios (`app/services/`)

### `pme_engine.py` — corazón algorítmico
Depende de `db`, `numpy` y los modelos de métricas/PME.

Funciones clave:
- `calcular_progreso_indicador(linea_base, valor_actual, meta, direccion)` → progreso, delta, cumplimiento y estado (`META_ALCANZADA`, `EN_PROGRESO`, `ESTABLE`, `RETROCESO`).
- `calcular_iea(...)` → Índice de Eficiencia de Acción (0–5), con penalización por sobregiro.
- `calcular_correlacion_pearson(x, y)` → coeficiente de Pearson.
- `determinar_semaforo(proyeccion, umbral_rojo, umbral_amarillo)` → `Rojo` / `Amarillo` / `Verde`.
- `proyectar_cumplimiento(serie, meta, x_indices)` → regresión lineal y proyección a fin de año.
- `desglosar_periodo(periodo)` → meses que componen el período: mes → 1 elemento, semestre (`2026-S1/S2`) → sus 4 meses, otro formato → sin cambios.
- `procesar_indicadores_accion(accion_id, periodo)` → **dispatcher**:
  - Si `periodo` es un mes → procesa ese mes (una fila en `indicadores_accion`).
  - Si `periodo` es un semestre → **desglosa en sus meses**: reparte las horas del semestre (más las filas `NULL`) en partes iguales, suma las horas ya mensuales del rango en su mes y crea **una fila por mes**; borra la fila agregada del semestre. Usa `horas=` para inyectar el reparto y `periodo_ref=` (el semestre) como respaldo para buscar mediciones/notas si el mes no tiene datos propios.
  - Con `DefinicionIndicador` activos → `_procesar_nuevo_modelo`; si no → `_procesar_legacy`.
- `obtener_impacto_individual(accion_id)` → impacto por alumno en el modelo legacy.
- `obtener_impacto_individual_nuevo(accion_id)` → impacto por alumno con múltiples indicadores.

**Helpers internos:** `_nota_promedio`, `_asistencia_promedio`, `_primer_periodo`, `_horas_por_estudiante`.

### `data_loader.py`
Funciones utilitarias para procesar CSV/Excel (`procesar_csv_acciones`, `procesar_excel_metricas`). **Actualmente no está conectado a ninguna ruta**; la carga Excel de acciones se implementó directamente en `routes/acciones.py` con pandas.

---

## 7. Dependencias entre archivos (mapa rápido)

```
run.py
 └─ app/__init__.py
     ├─ app/config.py
     ├─ app/extensions.py
     ├─ app/routes/auth.py ────────────► app/models/user.py
     ├─ app/routes/dashboard.py ───────► app/models/pme.py + metrics.py
     ├─ app/routes/ingesta.py ─────────► app/models/pme.py + metrics.py
     │                                   └─ app/services/pme_engine.py
     ├─ app/routes/acciones.py ────────► app/models/pme.py + metrics.py
     │                                   ├─ app/services/pme_engine.py
     │                                   └─ app/utils.py
     ├─ app/routes/reportes.py ────────► app/models/pme.py + metrics.py
     └─ app/routes/config.py ──────────► app/models/pme.py + user.py

Templates:
 app/templates/layouts/base.html  ← usado por TODAS las vistas (extiende)
 ├─ auth/login.html
 ├─ dashboard/index.html
 ├─ ingesta/index.html
 ├─ acciones/index.html / detalle.html
 ├─ reportes/index.html / ejecutivo.html
 └─ configuracion/index.html
```

### Qué se rompe si falta cada archivo

| Archivo ausente / modificado incorrectamente | Efecto |
|---|---|
| `app/extensions.py` | Imports circulares; `db` no disponible en modelos ni rutas. |
| `app/__init__.py` (imports de modelos) | `db.create_all()` no crea algunas tablas. |
| `app/models/pme.py` | No existen acciones/objetivos/dimensiones; F-1 y reportes fallan. |
| `app/models/metrics.py` | No existen estudiantes, notas ni indicadores; F-2/F-4 fallan. |
| `app/services/pme_engine.py` | `/ingesta/participacion` y `/acciones/detalle` fallan al calcular. |
| `app/templates/layouts/base.html` | Todas las vistas que lo extienden lanzan `TemplateNotFound`. |
| `app/templates/ingesta/index.html` | F-1 a F-4 sin interfaz. |
| `app/static/uploads/` | No se puede guardar el logo del establecimiento. |
| `instance/edugest_pme.db` | La app arranca vacía (sin establecimiento/usuarios/datos). |
| `seed.py` | No hay datos de prueba ni usuario admin inicial. |

---

## 8. Base de datos y seed

- **Motor:** SQLite (`instance/edugest_pme.db`).
- **Creación de tablas:** automática en `create_app()` mediante `db.create_all()`.
- **Datos iniciales:** `seed.py` (independiente) crea:
  - 1 establecimiento ("Liceo de Excelencia").
  - 1 usuario admin (`admin@liceo.cl` / `admin123`).
  - 4 cursos y ~60 estudiantes.
  - 10 acciones PME.
  - Registros mensuales de App Ponderado (notas/asistencia) para 5 asignaturas.
  - Métricas SIGE, participaciones e indicadores históricos.

> ⚠️ `seed.py` no crea `DefinicionIndicador`; esas se crean desde la UI (F-1) o automáticamente al crear una acción con campos legacy.

---

## 9. Endpoints relevantes (F-2 / integración AJAX)

| Método | Endpoint | Archivo | Devuelve |
|---|---|---|---|
| GET | `/ingesta/indicadores_de_accion/<accion_id>` | `routes/ingesta.py` | JSON con indicadores activos y su `asignatura` |
| GET | `/ingesta/periodos_estudiante?estudiante_id=&asignatura=` | `routes/ingesta.py` | JSON `{periodos: [...]}` |
| GET | `/ingesta/notas_estudiante?estudiante_id=&periodo=&asignatura=` | `routes/ingesta.py` | JSON `{existe, promedio_notas, porcentaje_asistencia}` (más reciente) |
| GET | `/ingesta/notas_periodos?estudiante_id=&asignatura=&desde=&hasta=` | `routes/ingesta.py` | JSON con `registros[]`, `promedio_notas`, `porcentaje_asistencia`, `nota_min/max`, `n_periodos`, `n_periodos_rango`, `periodos_faltantes[]`. Sin `desde`/`hasta` devuelve todos los periodos; con rango promedia **solo los meses que tienen registro** (deduplica por periodo, gana el más reciente) |
| POST | `/ingesta/app_ponderado` | `routes/ingesta.py` | Guarda `RegistroAppPonderado` |
| POST | `/ingesta/medicion_indicador` | `routes/ingesta.py` | Guarda `MedicionIndicador` |
| POST | `/ingesta/participacion` | `routes/ingesta.py` | Guarda `ParticipacionAccion` y dispara `pme_engine` |
| POST | `/ingesta/sige` | `routes/ingesta.py` | Guarda `MetricaSIGE` |
| POST | `/acciones/nueva` | `routes/acciones.py` | Crea `AccionPME` + `DefinicionIndicador` |
| GET | `/acciones/detalle/<id>` | `routes/acciones.py` | Vista de impacto por acción: KPIs, histórico mensual (`historico`), distribución de alumnos (`distribucion`), select de estado (`estados_accion`) y semestres con horas (`periodos_semestre`) |
| POST | `/acciones/cambiar_estado/<id>` | `routes/acciones.py` | Cambia `AccionPME.estado` validando contra `ESTADOS_ACCION` (`Planificada`, `En Ejecución`, `Finalizada`, `Cancelada`) y redirige al detalle |
| POST | `/acciones/recalcular/<id>` | `routes/acciones.py` | Vuelve a correr `procesar_indicadores_accion` para cada período con horas (meses primero, semestres al final); desglosa un semestre ya cargado en filas mensuales sin duplicar horas |
| GET | `/reportes/exportar_excel` | `routes/reportes.py` | Excel Matriz de Rendición |
| GET | `/reportes/auditoria` | `routes/reportes.py` | ZIP de trazabilidad |

---

## 10. Flujo de datos completo

```
F-1  (acciones.nueva_accion)
      → AccionPME
      → DefinicionIndicador (incluye asignatura)
F-2  (ingesta.cargar_app_ponderado)
      → RegistroAppPonderado (notas/asistencia)
F-2  (ingesta.cargar_medicion_indicador)
      → MedicionIndicador (valor de habilidad)
F-4  (ingesta.cargar_participacion)
      → ParticipacionAccion
      → pme_engine.procesar_indicadores_accion()
            → IndicadorAccion (IEA, IPA, Pearson, semáforo, proyección)
F-3  (ingesta.cargar_sige)
      → MetricaSIGE
Reportes / Dashboard
      ← leen AccionPME + IndicadorAccion + métricas
```

---

## 11. Consideraciones de mantenimiento

- **Límite de 500 líneas por archivo Python** definido en el README; `reportes.py` (304 líneas) y `pme_engine.py` (579 líneas) ya lo superan o están cerca. `pme_engine.py` debería dividirse si sigue creciendo.
- **`SQLALCHEMY_ECHO=True`** en desarrollo genera mucho ruido en consola (visible en los logs del usuario). Se puede desactivar en `DevelopmentConfig`.
- Las vistas dependen de **CDNs** (Tailwind, FontAwesome, Chart.js). Sin internet, la UI pierde estilos.
- No hay migraciones (Alembic/Flask-Migrate): los cambios de esquema en producción requerirían recrear la base o migrar manualmente.
- No hay control de acceso por rol: cualquier usuario autenticado puede acceder a `/configuracion` y crear usuarios.

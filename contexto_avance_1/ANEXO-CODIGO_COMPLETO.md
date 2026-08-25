# ANEXO - Mapa Técnico del Código (EduGest PME)

> **Fecha:** 25 de agosto de 2026
> **Enfoque:** Este documento NO contiene el código fuente completo. Describe qué hace cada función/módulo, cómo se enlazan entre sí y qué realizan al enlazarse.
> **Para ver el código real, abrir los archivos .py del proyecto.**

---

## 1. PUNTO DE ENTRADA Y CONFIGURACIÓN

### `run.py`
- **Propósito:** Punto de entrada de la aplicación.
- **Flujo:**
  1. Lee variable de entorno `FLASK_ENV` (default: `"development"`).
  2. Llama a `create_app(config_name)` desde `app/__init__.py`.
  3. Ejecuta `app.run(host="0.0.0.0", port=5000)`.
- **Enlace con:** `app/__init__.py` → `create_app()`.

### `app/config.py`
- **Clases:**
  - `Config` (base): Define `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (SQLite), `PERMANENT_SESSION_LIFETIME` (8h), umbrales del semáforo (`UMBRAL_SEMAFORO_ROJO=0.85`, `AMARILLO=0.95`), y carpeta de uploads.
  - `DevelopmentConfig`: Hereda de `Config`, `DEBUG=True`, `SQLALCHEMY_ECHO=True`.
  - `ProductionConfig`: `DEBUG=False`.
  - `TestingConfig`: SQLite en memoria, `WTF_CSRF_ENABLED=False`.
- **Diccionario:** `config_por_entorno` mapea nombres de entorno a clases.
- **Enlace con:** `app/__init__.py` → `app.config.from_object(...)`.

---

## 2. EXTENSIONES Y FACTORY

### `app/extensions.py`
- **Propósito:** Evitar imports circulares al separar la creación de extensiones de su inicialización.
- **Objetos:**
  - `db = SQLAlchemy()` — ORM, aún no vinculado a ninguna app.
  - `login_manager = LoginManager()` — Gestión de sesiones, aún no vinculado.
- **Enlace con:** `app/__init__.py` → `db.init_app(app)` y `login_manager.init_app(app)`.
- **Enlace con:** Todos los modelos (`user.py`, `pme.py`, `metrics.py`) → importan `db` desde aquí.

### `app/__init__.py` — `create_app(config_name)`
- **Propósito:** Application Factory. Crea y configura la app Flask.
- **Flujo de ejecución:**
  1. Crea instancia `Flask(__name__)`.
  2. Carga configuración desde `config_por_entorno` según el nombre recibido.
  3. Crea directorio de uploads si no existe.
  4. **Inicializa extensiones:** `db.init_app(app)`, `login_manager.init_app(app)`.
  5. **Configura login:** `login_view="auth.login"`, mensajes flash.
  6. **Import crítico:** `from app.models.user import User` → registra el `@login_manager.user_loader` definido en `user.py`. **Sin esta línea, Flask-Login falla con `Missing user_loader`.**
  7. Llama a `_registrar_blueprints(app)`.
  8. Dentro de `app.app_context()`: `db.create_all()` → crea tablas si no existen.
- **Función `_registrar_blueprints(app)`:**
  - Importa los 6 blueprints de `app.routes.*`.
  - Los registra con sus respectivos `url_prefix`.
  - Define ruta raíz `/` que redirige a `auth.login`.
- **Enlace con:** Todos los blueprints, todos los modelos (vía `db.create_all()`), `config.py`, `extensions.py`.

---

## 3. MODELOS (SQLAlchemy ORM)

### `app/models/__init__.py`
- **Propósito:** Paquete Python. Importa todos los modelos para que SQLAlchemy los descubra.
- **Enlace con:** `db` desde `extensions.py`, y los 4 archivos de modelos.

### `app/models/user.py`
- **Clase `User(UserMixin, db.Model)`**
  - **Tabla:** `users`
  - **Campos:** `id`, `email` (unique, index), `password_hash`, `nombre`, `rol`, `activo`, `created_at`, `establecimiento_id` (FK nullable → `establecimientos.id`).
  - **Relación:** `establecimiento` → `Establecimiento` (back_populates="usuarios").
  - **Métodos:**
    - `set_password(password)` → hashea con `generate_password_hash`.
    - `check_password(password)` → verifica con `check_password_hash`.
    - `es_admin()` → True si rol es Director o Administrador.
    - `es_sostenedor()` → True si rol es Sostenedor.
  - **Constantes de clase:** 5 roles posibles (`ROL_DIRECTOR`, `ROL_UTP`, etc.).
- **Función `load_user(user_id)`**
  - Decorada con `@login_manager.user_loader`.
  - Recibe un `user_id` (string desde cookie de sesión), lo convierte a `int`, busca en DB con `User.query.get()`.
  - **Enlace con:** `extensions.py` → `login_manager`. Esta función se ejecuta en CADA request para saber quién es el usuario actual.
- **Enlace con:** `extensions.py` (login_manager), `app/models/pme.py` (Establecimiento).

### `app/models/pme.py`
- **Clase `Establecimiento(db.Model)`**
  - **Tabla:** `establecimientos`
  - **Campos:** `id`, `nombre`, `rbd` (unique, index), `direccion`, `telefono`, `email_institucional`, `logo_url`, `activo`, `created_at`.
  - **Relaciones:** `usuarios`, `cursos`, `metricas_sige`, `estudiantes` (todas `lazy="dynamic"`).
- **Clase `DimensionPME(db.Model)`**
  - **Tabla:** `dimensiones_pme`
  - **Campos:** `id`, `nombre` (unique), `codigo` (unique), `descripcion`, `orden`.
  - **Relación:** `objetivos` → `ObjetivoPME`.
  - **Constantes:** Las 4 dimensiones oficiales del PME chileno.
- **Clase `ObjetivoPME(db.Model)`**
  - **Tabla:** `objetivos_pme`
  - **Campos:** `id`, `dimension_id` (FK), `nombre`, `descripcion`, `anio` (default 2026), `estado`.
  - **Relaciones:** `dimension` → `DimensionPME`, `acciones` → `AccionPME`.
- **Clase `AccionPME(db.Model)`**
  - **Tabla:** `acciones_pme`
  - **Campos:** `id`, `objetivo_id` (FK), `nombre`, `descripcion`, `presupuesto_asignado`, `presupuesto_ejecutado`, `estado` (default "Planificada"), `responsable`, `fecha_inicio/fin`, `meta_cualitativa/cuantitativa`, `indicador_medible`, `curso_objetivo`.
  - **Método:** `porcentaje_ejecucion_presupuesto()` → calcula % ejecutado vs asignado.
  - **Relaciones:** `objetivo` → `ObjetivoPME`, `participaciones` → `ParticipacionAccion`, `indicadores` → `IndicadorAccion`.
- **Clase `Curso(db.Model)`**
  - **Tabla:** `cursos`
  - **Campos:** `id`, `nombre`, `nivel`, `anio`, `establecimiento_id` (FK).
  - **Relaciones:** `establecimiento` → `Establecimiento`, `estudiantes` → `Estudiante`.
- **Enlace con:** `extensions.py` (db), `app/models/metrics.py` (Estudiante, ParticipacionAccion, IndicadorAccion), `app/models/user.py` (User vía Establecimiento).

### `app/models/metrics.py`
- **Clase `Estudiante(db.Model)`**
  - **Tabla:** `estudiantes`
  - **Campos:** `id`, `nombre`, `apellido`, `matricula` (unique, index), `curso_id` (FK), `establecimiento_id` (FK), `activo`.
  - **Property:** `nombre_completo` → concatena nombre + apellido.
  - **Relaciones:** `curso` → `Curso`, `establecimiento` → `Establecimiento`, `registros_app` → `RegistroAppPonderado`, `participaciones` → `ParticipacionAccion`.
- **Clase `RegistroAppPonderado(db.Model)`** — Formulario F-2
  - **Tabla:** `registros_app_ponderado`
  - **Campos:** `id`, `estudiante_id` (FK), `periodo` (formato "2026-03", index), `asignatura`, `promedio_notas`, `porcentaje_asistencia`, `bitacora`.
  - **Relación:** `estudiante` → `Estudiante`.
- **Clase `MetricaSIGE(db.Model)`** — Formulario F-3
  - **Tabla:** `metricas_sige`
  - **Campos:** `id`, `establecimiento_id` (FK), `anio`, `mes`, `matricula_oficial`, `asistencia_oficial_validada`, `calificaciones_consolidadas`, `observaciones`.
  - **Relación:** `establecimiento` → `Establecimiento`.
- **Clase `ParticipacionAccion(db.Model)`** — Formulario F-4
  - **Tabla:** `participaciones_accion`
  - **Campos:** `id`, `estudiante_id` (FK), `accion_id` (FK), `horas_asistencia`, `asistencia_talleres`.
  - **Relaciones:** `estudiante` → `Estudiante`, `accion` → `AccionPME`.
- **Clase `IndicadorAccion(db.Model)`** — Resultados del motor
  - **Tabla:** `indicadores_accion`
  - **Campos:** `id`, `accion_id` (FK), `mes` ("2026-03"), `iea`, `correlacion_pearson`, `estado_semaforo`, `proyeccion_cumplimiento`, `gasto_mes`.
  - **Relación:** `accion` → `AccionPME`.
- **Enlace con:** `extensions.py` (db), `app/models/pme.py` (Establecimiento, Curso, AccionPME).

---

## 4. RUTAS (Blueprints)

### `app/routes/auth.py` — Blueprint `auth_bp` (prefix: `/auth`)
- **Función `login()`** — `methods=["GET", "POST"]`
  - **GET:** Renderiza `auth/login.html` (formulario vacío con credenciales precargadas).
  - **POST:**
    1. Lee `email` y `password` del formulario.
    2. Busca usuario con `User.query.filter_by(email=email, activo=True).first()`.
    3. Si existe y `check_password()` es True → `login_user(user)`, flash "Bienvenido", redirect a `dashboard.index`.
    4. Si no → flash "Credenciales incorrectas", redirect a `auth.login`.
  - **Enlace con:** `app/models/user.py` (User), `extensions.py` (login_manager implícito vía `login_user`).
- **Función `logout()`** — `@login_required`
  1. Llama `logout_user()`.
  2. Flash "Sesión cerrada", redirect a `auth.login`.
  - **Enlace con:** Flask-Login.

### `app/routes/dashboard.py` — Blueprint `dashboard_bp` (prefix: `/dashboard`)
- **Función `index()`** — `@login_required`
  - Renderiza `dashboard/index.html`.
  - **ACTUALMENTE:** No pasa variables al template. Todo el contenido es estático/hardcodeado.
  - **Enlace con:** Template `dashboard/index.html`.

### `app/routes/ingesta.py` — Blueprint `ingesta_bp` (prefix: `/ingesta`)
- **Función `index()`** — `@login_required`
  - Renderiza `ingesta/index.html`.
  - **ACTUALMENTE:** No procesa POST. El formulario visual no tiene `action` definido.
  - **Enlace con:** Template `ingesta/index.html`.

### `app/routes/acciones.py` — Blueprint `acciones_bp` (prefix: `/acciones`)
- **Función `index()`** — `@login_required`
  - Renderiza `acciones/index.html`.
  - **ACTUALMENTE:** Muestra vista detalle hardcodeada (Taller de Refuerzo Matemático). No lee de DB.
  - **Enlace con:** Template `acciones/index.html`.

### `app/routes/reportes.py` — Blueprint `reportes_bp` (prefix: `/reportes`)
- **Función `index()`** — `@login_required`
  - Renderiza `reportes/index.html`.
  - **ACTUALMENTE:** Cards de descarga son estáticas. No genera archivos reales.
  - **Enlace con:** Template `reportes/index.html`.

### `app/routes/config.py` — Blueprint `config_bp` (prefix: `/configuracion`)
- **Función `index()`** — `@login_required`
  - Renderiza `configuracion/index.html`.
  - **ACTUALMENTE:** Formulario visual sin POST.
  - **Enlace con:** Template `configuracion/index.html`.

---

## 5. SERVICIOS (Lógica de Negocio)

### `app/services/pme_engine.py` — Motor Algorítmico

Este módulo contiene **funciones puras** (sin dependencias de Flask ni DB). Reciben datos, calculan, retornan resultados.

- **`calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia)`**
  - **Propósito:** Índice de Eficiencia de Acción. Mide cuánto impacto se generó por peso invertido.
  - **Fórmula:** `impacto = (delta_rendimiento * 0.6) + (delta_asistencia * 0.4)`; `recurso = (gasto/1M) + (horas/10)`; `IEA = min(5.0, (impacto/recurso) * 10)`.
  - **Retorna:** Float entre 0.0 y 5.0.
  - **Enlace con:** `seed.py` → se llama para cada acción/mes al generar datos de prueba. **NO se llama desde ninguna ruta aún.**

- **`calcular_correlacion_pearson(x, y)`**
  - **Propósito:** Correlación entre dos arrays (ej: horas de taller vs mejora en notas).
  - **Usa:** `scipy.stats.pearsonr`.
  - **Retorna:** Tupla `(r, p_value)` o `(None, None)` si datos insuficientes.
  - **Enlace con:** `seed.py` → calcula correlación entre participaciones y delta de notas por acción.

- **`determinar_semaforo(proyeccion, umbral_rojo=0.85, umbral_amarillo=0.95)`**
  - **Propósito:** Clasificar proyección de cumplimiento en Rojo/Amarillo/Verde.
  - **Retorna:** String `"Rojo"`, `"Amarillo"` o `"Verde"`.
  - **Enlace con:** `seed.py` → asigna semáforo a cada indicador mensual. Podría usarse en dashboard para alertas.

- **`proyectar_cumplimiento(valores_historicos, meta)`**
  - **Propósito:** Proyectar a fin de año usando regresión lineal simple (`numpy.polyfit`).
  - **Retorna:** Float entre 0.0 y 2.0 (capado).
  - **Enlace con:** `seed.py` → genera proyecciones mensuales. Ideal para el semáforo predictivo del dashboard.

### `app/services/data_loader.py` — Procesamiento de Archivos

- **`procesar_csv_acciones(file_stream)`**
  - **Propósito:** Leer CSV con pandas, retornar lista de diccionarios.
  - **Retorna:** `list[dict]` o `{"error": str}`.
  - **Estado:** Esqueleto. No valida columnas, no inserta en DB.
  - **Enlace con:** Ninguna ruta lo usa aún. Diseñado para la carga masiva del módulo Ingesta (F-1).

- **`procesar_excel_metricas(file_stream)`**
  - **Propósito:** Leer Excel (.xlsx) con pandas.
  - **Retorna:** `list[dict]` o `{"error": str}`.
  - **Estado:** Esqueleto. No valida columnas, no inserta en DB.
  - **Enlace con:** Ninguna ruta lo usa aún. Diseñado para F-2, F-3, F-4.

---

## 6. SEED (Datos de Prueba)

### `seed.py`
- **Propósito:** Script independiente que pobla la base de datos con datos pseudo-reales.
- **Importante:** Agrega `sys.path.insert(0, BASE_DIR)` al inicio para que Python encuentre el paquete `app` cuando se ejecuta desde la raíz del proyecto.
- **Flujo de ejecución:**
  1. Crea app con `create_app("development")`.
  2. Dentro de `app.app_context()`:
     3. `crear_establecimiento()` → 1 registro.
     4. `crear_usuario_admin(est.id)` → 1 usuario (admin@liceo.cl / admin123).
     5. `crear_dimensiones()` → 4 dimensiones PME.
     6. `crear_objetivos(dims)` → 2 objetivos por dimensión = 8 objetivos.
     7. `crear_acciones(objs)` → 10 acciones con presupuesto, estado, responsable, curso objetivo.
     8. `crear_cursos(est.id)` → 4 cursos (5° a 8° Básico).
     9. `crear_estudiantes(cursos, est.id)` → 15 estudiantes por curso = 60 estudiantes.
     10. `crear_registros_app_ponderado(ests)` → ~2,400 registros (5 asignaturas × 8 meses × 60 estudiantes).
     11. `crear_participaciones(ests, accs)` → estudiantes asisten a talleres de acciones de su curso.
     12. `crear_metricas_sige(est.id)` → 8 métricas mensuales (marzo-octubre).
     13. `crear_indicadores(accs)` → para cada acción, por cada mes:
         - Obtiene participaciones de la acción.
         - Calcula delta de notas (nota final - nota inicial) por estudiante.
         - Llama a `calcular_correlacion_pearson(horas_list, notas_delta_list)`.
         - Llama a `calcular_iea()` con datos simulados.
         - Llama a `proyectar_cumplimiento()` con gasto acumulado.
         - Llama a `determinar_semaforo()` con la proyección.
         - Crea registro `IndicadorAccion`.
- **Enlace con:** Todos los modelos, `app/services/pme_engine.py` (las 4 funciones del motor).

---

## 7. TEMPLATES (Jinja2)

### `templates/layouts/base.html`
- **Layout maestro** que extienden todos los demás templates.
- **Estructura:** Sidebar fijo morado (`bg-indigo-600`) a la izquierda (250px), área de contenido a la derecha.
- **Navegación:** Dashboard, Ingesta, Acciones, Reportes, Configuración. Cada uno con ícono FontAwesome.
- **Bloques Jinja2:** `{% block title %}`, `{% block content %}`.
- **CDN:** Tailwind CSS, FontAwesome 6.4.0.
- **Enlace con:** Todos los templates del sistema vía `{% extends "layouts/base.html" %}`.

### `templates/auth/login.html`
- **NO extiende base.html.** Es pantalla independiente (split 50/50).
- **Izquierda:** Imagen de fondo + branding EduGest.
- **Derecha:** Formulario POST a `{{ url_for('auth.login') }}`.
- **Campos:** email (precargado admin@liceo.cl), password (precargado admin123), establecimiento, año lectivo.
- **Muestra flash messages** con `get_flashed_messages(with_categories=true)`.
- **Enlace con:** `app/routes/auth.py` → función `login()`.

### `templates/dashboard/index.html`
- **Extiende:** `layouts/base.html`.
- **Contenido:** 4 KPI cards (Presupuesto, Cumplimiento, IEA, Alertas), gráfico placeholder, panel de alertas críticas, tabla de seguimiento.
- **Estado:** Todo hardcodeado. No recibe variables del backend.
- **Enlace con:** `app/routes/dashboard.py` → función `index()`.

### `templates/ingesta/index.html`
- **Extiende:** `layouts/base.html`.
- **Contenido:** Tabs F-1 a F-4. Panel carga masiva (drop zone). Panel ingesta manual con formulario visual.
- **Estado:** Formulario sin `action` ni `method` definidos. No procesa POST.
- **Enlace con:** `app/routes/ingesta.py` → función `index()`.

### `templates/acciones/index.html`
- **Extiende:** `layouts/base.html`.
- **Contenido:** Vista detalle de una acción específica (hardcodeada: Taller Matemática 8vo). Header con imagen, info de presupuesto/responsable/fechas. Gráfico circular SVG (Pearson 0.82). Gráfico de barras comparativo. Indicadores afectados.
- **Estado:** Datos hardcodeados. No lee de DB.
- **Enlace con:** `app/routes/acciones.py` → función `index()`.

### `templates/reportes/index.html`
- **Extiende:** `layouts/base.html`.
- **Contenido:** 3 cards de descarga rápida (PDF, Excel, ZIP). Configuración de reporte personalizado con date pickers, checkboxes de dimensiones, dropdown de cursos, toggle de anexos. Preview visual de PDF.
- **Estado:** Todo estático. No genera archivos reales.
- **Enlace con:** `app/routes/reportes.py` → función `index()`.

### `templates/configuracion/index.html`
- **Extiende:** `layouts/base.html`.
- **Contenido:** Tabs (Ajustes del Colegio activo, Parámetros, Usuarios, Integraciones). Formulario de info institucional con logo upload, nombre, RBD (readonly), dirección, teléfono, email.
- **Estado:** Formulario visual sin POST.
- **Enlace con:** `app/routes/config.py` → función `index()`.

---

## 8. MAPA DE FLUJO DE DATOS

### Flujo 1: Login de usuario
```
Usuario → POST /auth/login
    ↓
auth.py::login()
    ↓
User.query.filter_by(email=..., activo=True).first()
    ↓
user.check_password(password)
    ↓ (si OK)
login_user(user)  [Flask-Login]
    ↓
redirect → /dashboard/
    ↓
dashboard.py::index() → render_template("dashboard/index.html")
```

### Flujo 2: Generación de datos de prueba (seed.py)
```
seed.py
    ↓
create_app("development")
    ↓
crear_establecimiento() → INSERT INTO establecimientos
    ↓
crear_usuario_admin() → INSERT INTO users (con password hash)
    ↓
crear_dimensiones() → INSERT INTO dimensiones_pme (4 registros)
    ↓
crear_objetivos() → INSERT INTO objetivos_pme (8 registros)
    ↓
crear_acciones() → INSERT INTO acciones_pme (10 registros)
    ↓
crear_cursos() → INSERT INTO cursos (4 registros)
    ↓
crear_estudiantes() → INSERT INTO estudiantes (60 registros)
    ↓
crear_registros_app_ponderado() → INSERT INTO registros_app_ponderado (~2,400 registros)
    ↓
crear_participaciones() → INSERT INTO participaciones_accion
    ↓
crear_metricas_sige() → INSERT INTO metricas_sige (8 registros)
    ↓
crear_indicadores()
    ↓
Para cada acción:
    ParticipacionAccion.query.filter_by(accion_id=...).all()
    ↓
RegistroAppPonderado.query.filter_by(estudiante_id=...).order_by(periodo).all()
    ↓
calcular_correlacion_pearson(horas_list, notas_delta_list)
    ↓
calcular_iea(gasto, horas, delta_rend, delta_asist)
    ↓
proyectar_cumplimiento(valores_historicos, meta)
    ↓
determinar_semaforo(proyeccion)
    ↓
INSERT INTO indicadores_accion
```

### Flujo 3: Request autenticado (cualquier ruta protegida)
```
Usuario → GET /dashboard/
    ↓
@login_required  [Flask-Login]
    ↓
login_manager._load_user()  (llama a load_user(user_id) en user.py)
    ↓
User.query.get(int(user_id))  →  recupera usuario de la sesión
    ↓
Si OK → ejecuta dashboard.py::index()
    ↓
render_template("dashboard/index.html")
```

### Flujo 4: Carga masiva (DISEÑADO pero NO implementado)
```
Usuario → POST /ingesta/  (con archivo CSV)
    ↓
ingesta.py::index()  (debería aceptar POST)
    ↓
request.files['archivo'] → file_stream
    ↓
data_loader.py::procesar_csv_acciones(file_stream)
    ↓
pd.read_csv() → list[dict]
    ↓
Validar columnas, mapear a modelo AccionPME
    ↓
db.session.bulk_insert_mappings(AccionPME, registros)
    ↓
Recalcular indicadores automáticamente
    ↓
redirect → /dashboard/
```

---

## 9. DEPENDENCIAS ENTRE MÓDULOS

```
run.py
  └── app/__init__.py
        ├── app/config.py
        ├── app/extensions.py
        │     └── (usado por: models, routes, services)
        ├── app/models/user.py  ← registra user_loader en extensions.login_manager
        │     └── app/models/pme.py  (Establecimiento)
        ├── app/models/pme.py
        │     └── app/models/metrics.py  (Estudiante, etc.)
        ├── app/routes/auth.py
        │     └── app/models/user.py
        ├── app/routes/dashboard.py
        ├── app/routes/ingesta.py
        ├── app/routes/acciones.py
        ├── app/routes/reportes.py
        └── app/routes/config.py

seed.py
  └── app/__init__.py → create_app()
  └── app/extensions.py → db
  └── app/models/* (todos)
  └── app/services/pme_engine.py

app/services/pme_engine.py  ← NO depende de nadie (funciones puras)
app/services/data_loader.py  ← NO depende de nadie (solo pandas)
```

---

## 10. CONSTANTES Y VALORES CLAVE

| Constante | Ubicación | Valor | Uso |
|-----------|-----------|-------|-----|
| `UMBRAL_SEMAFORO_ROJO` | `app/config.py` | 0.85 | Semáforo rojo si proyección < 85% |
| `UMBRAL_SEMAFORO_AMARILLO` | `app/config.py` | 0.95 | Semáforo amarillo si proyección < 95% |
| `MAX_CONTENT_LENGTH` | `app/config.py` | 10 MB | Límite de upload de archivos |
| `ROL_DIRECTOR` | `app/models/user.py` | "Director" | Rol con permisos de admin |
| `GESTION_PEDAGOGICA` | `app/models/pme.py` | "Gestión Pedagógica" | Dimensión PME #1 |
| `LIDERAZGO_ESCOLAR` | `app/models/pme.py` | "Liderazgo Escolar" | Dimensión PME #2 |
| `CONVIVENCIA_ESCOLAR` | `app/models/pme.py` | "Convivencia Escolar" | Dimensión PME #3 |
| `GESTION_RECURSOS` | `app/models/pme.py` | "Gestión de Recursos" | Dimensión PME #4 |
| `ANIO_GESTION` | `seed.py` | 2026 | Año lectivo de datos de prueba |
| `NUM_ESTUDIANTES_POR_CURSO` | `seed.py` | 15 | 15 × 4 cursos = 60 estudiantes |
| `admin@liceo.cl` / `admin123` | `seed.py` | — | Credenciales de prueba |

---

## 11. BUGS Y OMESSIONES CONOCIDAS

1. **`scipy` NO está en `requirements.txt`** pero se importa en `pme_engine.py`. Agregar `scipy>=1.11`.
2. **Ninguna ruta (excepto auth) acepta POST.** Los formularios en templates envían POST pero las rutas solo definen `methods=["GET"]`, lo que causaría "Method Not Allowed".
3. **CSRF no está activo.** `Flask-WTF` está instalado pero no se usa en formularios.
4. **No hay manejo de errores 404/500.** Flask muestra páginas de error por defecto.
5. **El template `acciones/index.html` está hardcodeado** a una sola acción (Taller Matemática). No hay listado de acciones.
6. **El RBD en `configuracion/index.html` es "12345-6"** pero el real en seed es "78332482-2".
7. **El año en `configuracion/index.html` dice "2024"** pero el sistema usa 2026.

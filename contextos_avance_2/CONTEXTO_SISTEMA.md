¡Excelente práctica de ingeniería! Estos archivos te servirán como "memoria institucional" del proyecto y para retomarlo con cualquier IA sin perder contexto. Sugerencia: créalos dentro de una carpeta nueva `contexto_avance_2/` para mantener el orden con tus carpetas anteriores.


### Archivo 1: `contexto_avance_2/01-CONTEXTO_SISTEMA.md`


# CONTEXTO COMPLETO DEL SISTEMA — EduGest PME (Avance 2)
## Documento de contexto para IA / nueva conversación

> **Propósito**: Este documento permite que cualquier asistente de IA (o el propio desarrollador)
> retome el proyecto con contexto completo. Describe el estado REAL del código tras el "Avance 2".
> Última actualización: tras completar módulos de Ingesta, Acciones, Dashboard, Reportes y Configuración.



## 1. QUÉ ES EL PRODUCTO

**EduGest PME** es un sistema web (Flask) que mide el **impacto cuantitativo del Plan de
Mejoramiento Educativo (PME)** en establecimientos educacionales chilenos. Su propuesta de valor
comercial: responder a sostenedores y directores *"¿las acciones que financiamos realmente
mejoraron las notas/asistencia de los alumnos?"* mediante 3 indicadores calculados automáticamente:

| Indicador | Mide | Fórmula conceptual |
|---|---|---|
| **IEA** (Índice de Eficiencia de Acción) | Eficiencia económica (0.0–5.0) | Impacto pedagógico normalizado / recurso invertido, con penalización por sobregiro presupuestario |
| **Correlación de Pearson (r)** | Eficacia pedagógica (−1.0 a 1.0) | Horas de taller (F-4) vs mejora de notas (delta F-2) |
| **Semáforo + Proyección** | Riesgo de cumplimiento de meta | Regresión lineal de la serie grupal → proyección a noviembre vs meta. Verde ≥95%, Amarillo 85–95%, Rojo <85% (configurable) |



## 2. STACK Y ARQUITECTURA

- **Backend**: Python 3.9, Flask (Application Factory), SQLAlchemy, Flask-Login
- **BD**: SQLite (`instance/edugest_pme.db`) — MVP, migración a PostgreSQL en roadmap
- **Frontend**: Jinja2 + Tailwind CSS (CDN) + Font Awesome + Chart.js (CDN)
- **Datos**: Pandas + NumPy + openpyxl (Excel), zipfile (stdlib, ZIP auditoría)
- **Seed**: Faker (es_CL) — usuario `admin@liceo.cl` / `admin123`
- **Estructura**: `app/models` (pme, metrics, user), `app/routes` (auth, dashboard, ingesta,
  acciones, reportes, config), `app/services` (pme_engine, data_loader), `app/templates`
  (por módulo), `app/static/uploads` (logos).

**⚠️ Regla crítica de SQLite**: `db.create_all()` NO altera tablas existentes. Si se cambia un
modelo, hay que borrar `instance/edugest_pme.db` y re-ejecutar `seed.py`. Excepción: tablas
NUEVAS (ej. `configuracion_sistema`) se crean solas al reiniciar, sin perder datos.



## 3. MODELOS DE DATOS (estado actual)

### 3.1 `app/models/pme.py`

**Establecimiento**: nombre, rbd (inmutable), direccion, telefono, email_institucional, logo_url.

**DimensionPME**: 4 dimensiones oficiales (Gestión Pedagógica, Liderazgo Escolar, Convivencia
Escolar, Gestión de Recursos) con código y orden.

**ObjetivoPME**: pertenece a una dimensión; tiene anio (2026) y estado.

**AccionPME** (corazón del sistema):
- Identificación: `codigo_interno` (ej. ACC-2026-001, único, autogenerado), nombre, descripcion
- Presupuesto: `presupuesto_asignado`, `presupuesto_ejecutado`, `fuente_financiamiento`
  (SEP/PIE/Subvención/Otros)
- Gestión: estado (Planificada/En Ejecución/Suspendida/Finalizada/Cancelada), responsable,
  fecha_inicio, fecha_fin (db.Date → **requiere objetos date**, usar `parse_date()`)
- Motor: `indicador_tipo` ("Promedio Notas"|"Asistencia"), `unidad_medida`, `linea_base_valor`,
  `meta_valor` (floats — el motor SOLO funciona con estos numéricos), `meta_cuantitativa` (texto)
- `meta_cualitativa` = justificación de la inversión (auditoría)
- Método: `porcentaje_ejecucion_presupuesto()` (trunca a 100 — para detectar sobregiro usar
  cálculo directo en template)

**Curso**: nombre, nivel, anio, establecimiento_id.

**ConfiguracionSistema** (NUEVA en Avance 2, una fila por establecimiento):
- `anio_activo` (2026), `umbral_rojo` (0.85), `umbral_amarillo` (0.95),
  `peso_rendimiento` (0.6), `peso_asistencia` (0.4). El motor los lee en cada cálculo;
  si no hay fila, usa defaults.

### 3.2 `app/models/metrics.py`

**Estudiante**: nombre, apellido, matrícula única, curso_id, establecimiento_id, activo.
Property `nombre_completo`.

**RegistroAppPonderado** (datos F-2): estudiante_id, `periodo` (string "2026-08" — el motor
compara strings, deben ser EXACTOS entre F-2 y F-4), asignatura, promedio_notas,
porcentaje_asistencia, bitacora.

**MetricaSIGE** (datos F-3): establecimiento_id, anio, mes, matricula_oficial,
asistencia_oficial_validada, calificaciones_consolidadas, observaciones.

**ParticipacionAccion** (datos F-4): estudiante_id, accion_id, horas_asistencia,
asistencia_talleres, fecha_registro.

**IndicadorAccion** (resultado del motor): accion_id, mes (periodo), iea, correlacion_pearson,
estado_semaforo, proyeccion_cumplimiento, gasto_mes. Upsert por (accion_id, mes).



## 4. MOTOR ALGORÍTMICO (`app/services/pme_engine.py`)

### Funciones puras
- `calcular_iea(gasto, horas, delta_rend, delta_asist, presupuesto_asignado=None,
  peso_rendimiento=0.6, peso_asistencia=0.4)`:
  Normaliza escalas (notas recortadas ±2; asistencia ±10 dividida en 10) → impacto ponderado
  con pesos configurables (normalizados) / recurso (gasto en millones + horas/10) × 10.
  **Penalización por sobregiro**: si gasto > presupuesto → IEA ×= presupuesto/gasto. Rango 0–5.
- `calcular_correlacion_pearson(x, y)`: numpy corrcoef; devuelve (None, None) si <2 puntos.
  **Con 2 alumnos SIEMPRE da ±1** (dos puntos = línea perfecta); para valores intermedios
  se necesitan ≥4-5 alumnos.
- `determinar_semaforo(proyeccion, um_rojo=0.85, um_amar=0.95)` → "Rojo"/"Amarillo"/"Verde".
- `proyectar_cumplimiento(serie, meta, x_indices=None, mes_objetivo=11)`: regresión lineal
  con mes real como X (marzo=3 ... noviembre=11), proyecta al mes 11 y divide por la meta.

### Helpers anti-contaminación
`_nota_promedio(est_id, periodo)` y `_asistencia_promedio(...)`: promedian TODOS los registros
del alumno en el periodo (si hay 5 asignaturas, promedia las 5). `_primer_periodo(est_id)`:
periodo más antiguo con datos.

### Orquestador: `procesar_indicadores_accion(accion_id, periodo)`
Se dispara automáticamente al guardar el F-4. Pasos:
1. Acumula horas por estudiante (múltiples cargas se suman).
2. Para cada alumno con notas en el periodo: nota actual (promedio del periodo) y nota inicial
   (primer periodo o línea base de la acción) → delta individual.
3. Deltas del GRUPO según indicador_tipo ("Asistencia" usa asistencia, sino notas).
4. Lee `ConfiguracionSistema` (pesos y umbrales configurables).
5. Calcula IEA (con sobregiro), Pearson (horas vs deltas), serie grupal por periodo → proyección
   → semáforo. Upsert en IndicadorAccion.
**Nota**: los cambios de configuración solo aplican a cálculos FUTUROS (F-4 posteriores).

### `obtener_impacto_individual(accion_id)`
Para la vista de detalle: por alumno devuelve horas acumuladas, nota inicial/actual, delta,
asistencia actual y clasificación (Mejora alta ≥+0.3 / Mejora leve ≥+0.1 / Estable / Retroceso /
Sin datos). Ordenado por horas desc. Alimenta la tabla y el scatter plot.



## 5. MÓDULOS Y RUTAS (estado actual)

### 5.1 Auth (`/auth`)
Login funcional con Flask-Login. **Pendiente verificar**: ruta `/auth/logout` (el botón del
sidebar de `base.html` ya apunta ahí). Login view = "auth.login".

### 5.2 Dashboard (`/dashboard`) — `routes/dashboard.py`
- `index`: suma global de presupuesto (asignado/ejecutado), % ejecución global, alertas
  (acciones Rojo/Amarillo con IEA y proyección), conteo por semáforo para doughnut Chart.js.
- `/api/datos-grafico`: JSON con labels/presupuesto por acción (endpoint opcional para AJAX).
- Template: KPIs dinámicos, doughnut semáforo, lista de alertas, tabla de seguimiento,
  botón Exportar → Matriz de Rendición.

### 5.3 Ingesta (`/ingesta`) — `routes/ingesta.py` (4 tabs en un solo template)
- **F-1 Registro de Acciones** (tab1): formulario completo (dimensión/objetivo, fuente
  financiamiento, responsable, fechas date, estado, indicador, unidad de medida, línea base,
  meta valor, meta cuantitativa, justificación) → POST a `acciones.nueva_accion`.
  **Gestión masiva Excel**: descargar plantilla, subir archivo → preview en sesión → modal de
  validación → guardar masivamente o cancelar.
- **F-2 App Ponderado** (tab2): registro individual de notas/asistencia por alumno-periodo-
  asignatura con bitácora. Select de estudiantes muestra curso.
- **F-3 SIGE** (tab3): métricas oficiales mensuales con observaciones.
- **F-4 Participación** (tab4): **carga masiva** — select de acción (con placeholder obligatorio
  "⚠️ Seleccione..."), periodo, horas comunes al grupo, selector con **filtro por curso**,
  botones "Seleccionar todos (visibles)"/"Limpiar", checkboxes `estudiantes[]`. Al guardar
  dispara el motor y el flash **confirma el nombre de la acción** (evita cargar en acción
  equivocada).

### 5.4 Acciones (`/acciones`) — `routes/acciones.py`
- `index`: tabla de todas las acciones (código, nombre, responsable, estado con colores,
  presupuesto) → link a detalle.
- `detalle/<id>`: header card con presupuesto asignado vs ejecutado (barra verde/amarilla/roja,
  alerta de sobregiro >100%), descripción, justificación, fechas, responsable. Analítica:
  círculo SVG Pearson con texto interpretativo (incluye casos negativos), gráfico barras
  Meta vs Proyección (Chart.js), indicadores afectados (línea base, meta, IEA, semáforo),
  **tabla de impacto individual por alumno + scatter plot horas vs delta** (Chart.js).
- `nueva_accion` (GET/POST): crea acción con código automático ACC-2026-NNN y `parse_date()`.
- Excel: `plantilla_excel` (descarga .xlsx), `cargar_excel` (lee con pandas, guarda en
  `session['preview_data']`), `guardar_excel` (inserta masivo), `cancelar_excel`.

### 5.5 Reportes (`/reportes`) — `routes/reportes.py`
- `index`: 3 cards (PDF, Excel, ZIP) + formulario "Reporte Personalizado" (dimensiones desde
  BD, cursos, rango fechas → JS arma query params) + vista previa con datos REALES del
  establecimiento (nombre, RBD, semáforos, ejecución presupuestaria, IEA promedio).
- `/ejecutivo`: **documento HTML imprimible A4** (`reportes/ejecutivo.html`, NO extiende
  base.html) con KPIs, tabla de semáforos, detalle de acciones, alertas (incluye sobregiros)
  y firmas Director/Sostenedor. Botón "Imprimir/Guardar como PDF" (window.print()).
  *Decisión de diseño: PDF real (reportlab/weasyprint) quedó para roadmap; el HTML imprimible
  evita dependencias problemáticas en Windows.*
- `/exportar_excel`: Matriz de Rendición (20 columnas: código, dimensión, presupuestos,
  fuentes, justificación, IEA, Pearson, proyección, semáforo). **Acepta filtros** por query
  params: `dimensiones` ("1,3"), `curso`, `desde`, `hasta`.
- `/auditoria_zip`: ZIP con 5 archivos: matriz Excel + CSVs (indicadores históricos,
  participaciones de alumnos, métricas SIGE) + README con resumen global.

### 5.6 Configuración (`/configuracion`) — `routes/config.py` (4 tabs)
- **Colegio**: editar establecimiento (RBD readonly) + subir logo a `static/uploads/`
  (werkzeug secure_filename, acepta png/jpg/jpeg/gif, auto-submit al elegir archivo).
- **Algoritmo** (🔑 configurable por cliente): umbrales semáforo con **preview en vivo de la
  barra roja/amarilla/verde** (JS oninput), año lectivo, pesos IEA (validación: rojo < amarillo,
  pesos ≥0; se envían en % y se dividen /100).
- **Usuarios**: tabla con estado, crear usuario (email único, password ≥6 chars, rol desde
  constantes del modelo User detectadas dinámicamente), toggle activar/desactivar con
  protección de no desactivarse a sí mismo.
- **Integraciones**: SIGE y App Ponderado como cards informativas "Fase 2 — Pendiente".

### 5.7 Base (`templates/layouts/base.html`)
Sidebar con navegación, flash messages categorizados (error/success/info/warning, fixed
top-right), **botón logout** (ícono sign-out), Chart.js y Tailwind por CDN.
Filtro Jinja registrado: `from_json`.



## 6. FLUJO DE DATOS CRUZADO (lo más importante para entender el sistema)

```
F-1 (Acción) ──── define ────> presupuesto, línea_base, meta_valor, indicador_tipo
     │
F-2 (App Ponderado) ─ registros de notas/asistencia por alumno+periodo+asignatura
     │                   (formato periodo EXACTO: "2026-08")
     │
F-4 (Participación) ─ horas de taller por alumno, EN UNA ACCIÓN y PERIODO
     │
     └──── AL GUARDAR F-4 ────> procesar_indicadores_accion(accion_id, periodo)
                                      │
                    cruza F-1 + F-2 + F-4 → IEA, Pearson, Proyección, Semáforo
                                      │
                                      ▼
                         tabla IndicadorAccion (upsert por acción+periodo)
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        Dashboard               Detalle Acción            Reportes
        (KPIs, alertas,    (Pearson visual, impacto   (PDF ejecutivo, Excel
         doughnut)           individual, scatter)      matriz, ZIP auditoría)
```

**El F-3 (SIGE) NO alimenta el motor**: es dato oficial global para auditoría/reportes y
comparación externa.

### Escenario de prueba validado (usar para testing)
1. F-1: acción "Promedio Notas", línea base 4.0, meta 5.5, presupuesto 500.000, ejecutado 850.000.
2. F-2: 2+ alumnos con nota ~4.0 en "2026-03" y notas mejores en "2026-08".
3. F-4: mismos alumnos, periodo "2026-08", horas DISTINTAS por alumno (5 y 45).
4. Detalle esperado: Pearson ≈ +1.0 (positivo), IEA BAJO por sobregiro (~0.7), semáforo según
   tendencia.

### Bugs resueltos (histórico — no reintroducir)
- `db.create_all()` no veía modelos no importados → importar TODOS en `__init__.py`.
- Columnas nuevas en SQLite → borrar .db y re-seed.
- Fechas de formularios llegan como string → `parse_date()` (maneja str/pd.Timestamp/date).
- IEA mal escalado (usaba asistencia absoluta 85 como delta) → normalización de escalas.
- Pearson contaminado por seed (5 registros/asignatura por periodo) → `_nota_promedio` promedia.
- Pearson = -1 con 2 alumnos: correcto matemáticamente si la línea baja; verificar horas.
- Participaciones en acción equivocada (select se reseteaba) → placeholder obligatorio +
  flash con nombre de acción.
- Scripts auxiliares en raíz: `limpiar_prueba.py`, `diagnosticar_participaciones.py`.



## 7. DEPENDENCIAS (`requirements.txt`)
```
flask, flask-login, flask-sqlalchemy, sqlalchemy, pandas, numpy, openpyxl, faker
```



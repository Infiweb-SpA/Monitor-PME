# Puntos de Revisión — Formularios, Datos y Lógica

Este documento lista los puntos que **requieren revisión o corrección**, ordenados por prioridad. Cada punto indica dónde está, qué ocurre y qué se recomienda.

Leyenda de prioridad:
- 🔴 **Alta** — afecta la integridad de datos o impide completar el flujo.
- 🟡 **Media** — afecta la experiencia o la exactitud de un cálculo.
- 🟢 **Baja** — deuda técnica o mejora deseable.

---

## 1. Formularios (Frontend)

### 🔴 1.1 El campo “Asignatura” de F‑2 Parte 1 es `readonly` por defecto
- **Archivo:** `app/templates/ingesta/index.html` (línea ~243)
- **Problema:** el input `#f2-asignatura` nace con `readonly`. Si el usuario **no selecciona una Acción / Taller**, el campo permanece bloqueado, vacío y además es `required`. El navegador impide enviar el formulario y el usuario no puede escribir la asignatura manualmente.
- **Recomendación:** quitar `readonly` del HTML y aplicarlo solo por JS cuando realmente se derive una asignatura desde la acción (`asigInp.readOnly = !!asig`). Alternativamente, dejar de marcar `required` cuando no hay acción.

### 🔴 1.2 La asignatura derivada depende del **primer** indicador no transversal
- **Archivo:** `app/templates/ingesta/index.html` (funciones `setAsignaturaFromAccion` y precarga de mediciones) + `app/routes/ingesta.py`
- **Problema:** si una acción tiene varios indicadores con asignaturas distintas (Matemáticas, Lenguaje, etc.), la UI toma la primera que encuentra y precarga notas de esa asignatura. No hay forma de elegir cuál indicador/asignatura se está midiendo.
- **Recomendación:** añadir un selector de indicador (o de asignatura) en F‑2; o decidir a nivel de acción una única asignatura.

### ✅ 1.3 F‑2 Parte 2 mantiene “Periodo” como texto libre *(RESUELTO)*
- **Archivo:** `app/templates/ingesta/index.html` (`#med-periodo`)
- **Estado:** el período ahora es un `<select>` dinámico construido con `/ingesta/periodos_estudiante` (mismo patrón que F‑2 Parte 1), más dos opciones fijas de promedio semestral (`2026-S1`, `2026-S2`). La precarga se dispara en `change` (no en `blur`), por lo que también se ejecuta antes de enviar el formulario.
- **Detalle:** el bloque de referencia usa el nuevo endpoint `/ingesta/notas_periodos`, que acepta `desde`/`hasta` para promediar un rango de meses (ver §4.4).

### 🟡 1.4 El catálogo de asignaturas puede quedar vacío
- **Archivo:** `app/routes/ingesta.py` (`index`) + `app/templates/ingesta/index.html` (`window.ASIGNATURAS`)
- **Problema:** `asignaturas` se obtiene con `SELECT DISTINCT asignatura FROM registros_app_ponderado`. Si la base no tiene registros de App Ponderado, el `<select>` de asignaturas en F‑1 solo muestra “Transversal”, impidiendo asociar una asignatura.
- **Recomendación:** usar un catálogo estático de respaldo (Matemáticas, Lenguaje, Ciencias, Historia, Inglés, etc.) y combinarlo con las asignaturas ya registradas.

### 🟡 1.5 El select “Acción / Taller” de F‑2 Parte 1 no se usa en el backend
- **Archivo:** `app/templates/ingesta/index.html` (`name="accion_ref"`) + `app/routes/ingesta.py`
- **Problema:** `cargar_app_ponderado` ignora `accion_ref`; solo se usa en el frontend para derivar la asignatura. No queda registrada la relación taller ↔ registro.
- **Recomendación:** si se necesita trazabilidad, guardar la acción/indicador en el registro o en la bitácora.

### 🟢 1.6 Comparación de “Grupo” sin uso en el motor
- **Archivo:** `app/templates/ingesta/index.html` (línea ~263) + `app/models/metrics.py`
- **Problema:** el formulario F‑2 captura `grupo` (“Intervenido”/“Control”), pero el motor de cálculo no separa ni compara grupos de control.
- **Recomendación:** implementar el análisis de impacto real Intervenido vs Control o documentar que aún no está operativo.

---

## 2. Datos y persistencia

### 🔴 2.1 `RegistroAppPonderado`: cada envío crea un registro nuevo (duplicados)
- **Archivo:** `app/routes/ingesta.py` (`cargar_app_ponderado`)
- **Problema:** siempre se hace `db.session.add(RegistroAppPonderado(...))`. Si el usuario guarda dos veces el mismo estudiante/período/asignatura, quedan filas duplicadas. `notas_estudiante` toma la más reciente por `fecha_registro`, pero `_nota_promedio` (motor) promedia **todas** las filas, distorsionando resultados.
- **Recomendación:** definir una restricción única `(estudiante_id, periodo, asignatura, grupo)` y hacer *upsert* (actualizar si existe, insertar si no).

### 🔴 2.2 `MedicionIndicador`: cada envío crea una medición nueva
- **Archivo:** `app/routes/ingesta.py` (`cargar_medicion_indicador`)
- **Problema:** no se verifica si ya existe una medición para `(indicador_def_id, estudiante_id, periodo)`. El motor construye un diccionario `meds_map` con esa clave, por lo que las filas duplicadas se sobrescriben de forma no determinista (la última leída gana).
- **Recomendación:** *upsert* por `(indicador_def_id, estudiante_id, periodo)` y restricción única.

### 🔴 2.3 El motor promedia notas de **todas** las asignaturas del período
- **Archivo:** `app/services/pme_engine.py` (`_nota_promedio`, `_asistencia_promedio`)
- **Problema:** estas funciones filtran solo por `estudiante_id` y `periodo`, sin `asignatura`. Por lo tanto:
  - El flujo legacy y el “indicador automático” de `_procesar_nuevo_modelo` usan un promedio que mezcla Matemáticas, Lenguaje, Ciencias, etc.
  - No reflejan la asignatura asociada al indicador/taller.
- **Recomendación:** añadir parámetro `asignatura` y filtrar; para indicadores con `DefinicionIndicador.asignatura`, usarla. Si no hay asignatura, documentar que es promedio general.

### 🔴 2.4 El indicador automático no guarda `asignatura`
- **Archivo:** `app/routes/acciones.py` (creación del `DefinicionIndicador` básico, ~líneas 98–108)
- **Problema:** al crear una acción con campos legacy (`indicador_tipo`, `linea_base_valor`, `meta_valor`), se genera un `DefinicionIndicador` sin `asignatura`. La UI lo muestra como “Transversal” y F‑2 no puede derivar la asignatura para precargar notas.
- **Recomendación:** agregar el campo “Asignatura” al bloque básico de F‑1 y guardarlo en `DefinicionIndicador.asignatura`.

### 🟡 2.5 `AccionPME.presupuesto_ejecutado` se replica en cada período
- **Archivo:** `app/services/pme_engine.py` (`_procesar_legacy` y `_procesar_nuevo_modelo`)
- **Problema:** `gasto_mes = accion.presupuesto_ejecutado` (total acumulado) se guarda igual para cada período. El IEA mensual se calcula con el gasto total, no con el gasto del mes.
- **Recomendación:** registrar gasto por período (nueva tabla o campo mensual) o aclarar que el IEA es acumulado.

### ✅ 2.6 Las horas de participación no se filtran por período *(RESUELTO)*
- **Archivo:** `app/services/pme_engine.py` (`_horas_por_estudiante`) + `app/models/metrics.py` (`ParticipacionAccion.periodo`)
- **Estado:** `ParticipacionAccion` tiene columna `periodo` (nullable, `"YYYY-MM"` o `"YYYY-S1/S2"`), que F-4 guarda desde un select. `_horas_por_estudiante(accion_id, periodo)` filtra por ese periodo y suma además las filas `NULL` (legado, compatibles con datos previos). Los reportes de impacto individual siguen usando el total acumulado (sin filtro).
- **Nota:** la columna se agrega automáticamente al arrancar la app (`_asegurar_columna` en `app/__init__.py`), ya que el proyecto no usa Flask-Migrate.

### 🟡 2.7 `MetricaSIGE.establecimiento_id` está fijo en 1
- **Archivo:** `app/routes/ingesta.py` (`cargar_sige`)
- **Problema:** `establecimiento_id = 1` está *hardcodeado*. Si el sistema se usa con más de un establecimiento, los datos quedan mal asignados.
- **Recomendación:** obtenerlo de `current_user.establecimiento_id` o de `Establecimiento.query.first()`, y validar su existencia.

### 🟡 2.8 `MetricaSIGE.calificaciones_consolidadas` nunca se completa
- **Archivo:** `app/routes/ingesta.py` (`cargar_sige`) + `app/templates/ingesta/index.html` (F‑3)
- **Problema:** el modelo y los reportes contemplan `calificaciones_consolidadas`, pero el formulario F‑3 no tiene campo para ingresarla y la ruta no la guarda.
- **Recomendación:** agregar el campo al formulario y a la ruta, o eliminar la columna de los reportes.

### 🟡 2.9 `ParticipacionAccion.asistencia_talleres` nunca se asigna
- **Archivo:** `app/routes/ingesta.py` (`cargar_participacion`) + `app/models/metrics.py`
- **Problema:** F‑4 solo envía `horas_asistencia`; `asistencia_talleres` queda en 0. Los reportes de auditoría muestran siempre 0 talleres asistidos.
- **Recomendación:** añadir el campo al formulario o calcularlo a partir de las horas.

### 🟢 2.10 Sin restricción única en `IndicadorAccion(accion_id, mes)`
- **Archivo:** `app/models/metrics.py`
- **Problema:** el motor hace *upsert* con `.first()`, pero la base permite duplicados si hay concurrencia o ejecuciones simultáneas.
- **Recomendación:** agregar `UniqueConstraint("accion_id", "mes")`.

---

## 3. Motor de cálculo (`app/services/pme_engine.py`)

### 🟡 3.1 `cumplimiento` no respeta `MENOR_ES_MEJOR`
- **Función:** `calcular_progreso_indicador`
- **Problema:** `cumplimiento = valor_actual / meta * 100` siempre asume que mayor es mejor. Para indicadores donde menor es mejor (ej. deserción, conflictos), el porcentaje de cumplimiento puede ser incorrecto o >100%.
- **Recomendación:** calcular cumplimiento según `direccion` (`meta / valor_actual` cuando `MENOR_ES_MEJOR`).

### 🟡 3.2 El “indicador principal” para proyección depende del orden de la BD
- **Función:** `_procesar_nuevo_modelo` (`ind_ppal = resultados[0]["def"]`)
- **Problema:** `resultados` se llena en el orden en que SQLAlchemy devuelve las definiciones; no hay criterio explícito (peso, orden, tipo). La proyección y el semáforo pueden cambiar si cambia el orden.
- **Recomendación:** elegir el indicador principal por mayor peso o agregar un campo `orden`/`es_principal` en `DefinicionIndicador`.

### 🟡 3.3 Proyección con pocos datos puede ser engañosa
- **Función:** `proyectar_cumplimiento`
- **Problema:** con un solo período devuelve el cociente actual/meta; con dos períodos la regresión es muy sensible. El semáforo puede marcar “Verde” o “Rojo” con información insuficiente.
- **Recomendación:** exigir un mínimo de períodos (ej. 3) para proyectar y mostrar “Sin datos suficientes” si no se cumple.

### 🟡 3.4 `_procesar_nuevo_modelo` no corre si no hay mediciones
- **Función:** `procesar_indicadores_accion`
- **Problema:** si la acción tiene `DefinicionIndicador` activos pero aún no hay `MedicionIndicador`, `resultados` queda vacío y retorna `None` (no se crea `IndicadorAccion`), incluso si existen notas en App Ponderado.
- **Recomendación:** documentar que primero deben registrarse mediciones en F‑2 Parte 2; o usar las notas como respaldo cuando el tipo de indicador sea `NOTA`/`ASISTENCIA`.

### 🟢 3.5 `calcular_iea` usa supuestos de escala fijos
- **Función:** `calcular_iea`
- **Problema:** normaliza `delta_rendimiento` a ±2 y `delta_asistencia` a ±10, y el recurso como `gasto/1.000.000 + horas/10`. Son supuestos razonables para el prototipo, pero deben validarse con datos reales.
- **Recomendación:** parametrizar estos factores en `ConfiguracionSistema` si se busca rigor.

---

## 4. Backend / rutas

### ✅ 4.1 Conversión `int()` sin manejo de errores *(RESUELTO)*
- **Archivo:** `app/routes/ingesta.py` (`periodos_estudiante`, `notas_estudiante`, `notas_periodos`)
- **Estado:** los tres endpoints validan `estudiante_id` y devuelven `{"error": ...}` con código 400 en lugar de lanzar `ValueError` → 500.

### 🟡 4.2 `acciones.nueva_accion` puede crear indicadores duplicados
- **Archivo:** `app/routes/acciones.py` (~líneas 91–113)
- **Problema:** si el formulario envía `indicador_tipo` + `linea_base_valor` + `meta_valor`, se crea automáticamente un `DefinicionIndicador` “básico”. Si además el usuario agregó indicadores personalizados con el mismo nombre/tipo, quedan duplicados.
- **Recomendación:** crear el básico solo si no se enviaron indicadores personalizados, o unificar en un solo mecanismo.

### 🟡 4.3 `cargar_medicion_indicador` no dispara el motor
- **Archivo:** `app/routes/ingesta.py`
- **Problema:** guardar mediciones no actualiza `IndicadorAccion`; el usuario debe ir a F‑4 y registrar participación para que se ejecute `procesar_indicadores_accion`. El mensaje flash lo indica, pero es un paso extra fácil de omitir.
- **Recomendación:** disparar el motor también al guardar mediciones (si hay período y datos suficientes), o dejar un botón “Recalcular”.

### 🟡 4.4 Formatos de período inconsistentes
- **Archivos:** `app/templates/ingesta/index.html` (F‑2 Parte 1, F‑2 Parte 2, F‑4) + `app/models/metrics.py`
- **Estado:** los tres formularios usan ahora `<select>` con valores estandarizados (`YYYY-MM`), por lo que el riesgo de escritura libre desaparece en la UI. Siguen existiendo posibles filas históricas con formatos libres (`2026-T1`, `Agosto`) que el motor no encontrará.
- **Nota:** F‑2 Parte 2 y F‑4 pueden guardar los valores semestrales `2026-S1` / `2026-S2` (rango fijo de meses). Al procesar un semestre el motor lo **desglosa en sus meses** (reparto equitativo de horas) y usa el semestre como respaldo para buscar mediciones/notas, así que las filas semestrales sí se aprovechan.
- **Recomendación:** depurar o migrar filas históricas con formato distinto de `YYYY-MM`.

### 🟢 4.5 Sin protección CSRF
- **Archivos:** todos los formularios POST.
- **Problema:** no se usa Flask-WTF ni tokens CSRF.
- **Recomendación:** añadir Flask-WTF o CSRFProtect en producción.

### 🟢 4.6 Sin autorización por roles
- **Archivo:** `app/routes/*.py`
- **Problema:** `@login_required` protege el acceso, pero cualquier usuario autenticado puede entrar a `/configuracion`, crear usuarios o modificar parámetros.
- **Recomendación:** implementar decoradores de rol (`admin`, `director`, `sostenedor`, etc.).

---

## 5. Consistencia de la información mostrada

### 🟡 5.1 “Asignatura: Transversal” en mediciones
- **Archivo:** `app/templates/ingesta/index.html` (select `#med-periodo` y render de indicadores en F‑2 Parte 2)
- **Problema:** si `DefinicionIndicador.asignatura` es `NULL`, se muestra “Transversal” y no hay notas que precargar.
- **Estado parcial:** ahora el select de período muestra un aviso explícito (`#med-periodo-hint`): *"La acción no tiene asignatura asociada (transversal): no hay notas que precargar."*
- **Pendiente:** permitir asociar la asignatura desde F‑1 y mostrar el aviso también junto a cada indicador.

### 🟡 5.2 Mensaje de precarga exitosa no distingue el origen
- **Archivo:** `app/templates/ingesta/index.html`
- **Problema:** el texto “Precargado desde App Ponderado” se muestra igual si el dato viene de un registro reciente o de uno duplicado/antiguo.
- **Recomendación:** incluir período y fecha del registro usado, y advertir si hay múltiples registros para el mismo período.

### 🟢 5.3 `window.ASIGNATURAS` se inyecta con `tojson`
- **Archivo:** `app/templates/ingesta/index.html` (línea 6)
- **Observación:** funciona correctamente, pero si se migra a CSP estricta habría que usar un `data-*` o un endpoint JSON.
- **Recomendación:** sin acción inmediata; considerar endpoint `/ingesta/asignaturas` si se endurece la seguridad.

---

## 6. Deuda técnica

| Punto | Ubicación | Detalle | Prioridad |
|---|---|---|---|
| `SQLALCHEMY_ECHO=True` en desarrollo | `app/config.py` | Inunda la consola con cada consulta SQL. | 🟢 |
| `data_loader.py` sin uso | `app/services/data_loader.py` | Funciones de CSV/Excel no conectadas a rutas. | 🟢 |
| `pme_engine.py` supera 500 líneas | `app/services/pme_engine.py` | El README exige máximo 500 líneas por archivo `.py`. | 🟢 |
| Sin migraciones | proyecto | No hay Flask-Migrate/Alembic; cambios de esquema requieren recrear la BD. | 🟡 |
| Dependencia de CDNs | `app/templates/layouts/base.html` | Tailwind/FontAwesome/Chart.js requieren internet. | 🟢 |
| `instance/edugest_pme.db` no versionada | `instance/` | Cada entorno debe ejecutar `seed.py`. | 🟢 |
| `seed.py` no crea `DefinicionIndicador` | `seed.py` | Las acciones sembradas no tienen indicadores nuevos; F‑2 Parte 2 aparece vacío hasta crear uno en F‑1. | 🟡 |

---

## 7. Checklist rápido de revisión

### Formularios
- [ ] F‑1: el select de asignaturas muestra opciones aunque no haya registros de App Ponderado.
- [ ] F‑1: la asignatura se guarda en `DefinicionIndicador.asignatura`.
- [ ] F‑2 Parte 1: se puede enviar el formulario sin seleccionar acción (asignatura manual).
- [ ] F‑2 Parte 1: el período se carga dinámicamente al elegir estudiante + asignatura.
- [ ] F‑2 Parte 1: las notas se precargan y quedan en solo lectura.
- [x] F‑2 Parte 2: el período es consistente con Parte 1 (select dinámico + semestres).
- [x] F‑2 Parte 2: la precarga se ejecuta antes del submit (evento `change`).
- [ ] F‑2 Parte 2: se muestra claramente si el indicador es transversal.

### Datos
- [ ] No se crean duplicados en `RegistroAppPonderado`.
- [ ] No se crean duplicados en `MedicionIndicador`.
- [ ] Las notas usadas por el motor filtran por asignatura cuando corresponde.
- [ ] El gasto mensual no repite el total acumulado.
- [x] Las horas de participación se filtran por período (columna `periodo` + `_horas_por_estudiante(accion_id, periodo)`).
- [ ] `MetricaSIGE` usa el establecimiento correcto.
- [ ] `calificaciones_consolidadas` y `asistencia_talleres` se capturan o se eliminan de reportes.

### Motor
- [ ] `MENOR_ES_MEJOR` calcula bien el cumplimiento.
- [ ] La proyección exige un mínimo de períodos.
- [ ] El indicador principal está definido explícitamente.
- [ ] El motor se dispara tras guardar mediciones (o hay botón de recálculo).

### Seguridad / operación
- [ ] CSRF en formularios POST.
- [ ] Autorización por rol en `/configuracion`.
- [ ] Formato de período estandarizado (`YYYY-MM`).
- [ ] Migraciones de base de datos.
- [ ] `SQLALCHEMY_ECHO` desactivado fuera de depuración.

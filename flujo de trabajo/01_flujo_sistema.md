# Flujo de Trabajo — Cómo Funciona el Sistema EduGest PME

## Resumen de flujo general (F-1 → F-2 → F-3)

El sistema opera en 3 fases secuenciales. El usuario debe completar cada paso para que los datos se propaguen correctamente entre formularios.

---

## F-1: Definición de Indicadores de Acción

**Objetivo:** Crear los indicadores que medirán una acción (taller/intervención).

### Campos y orden de llenado

| Paso | Campo | Origen / Ejemplo | Dependencia |
|---|---|---|---|
| 1 | **Acción / Taller** | Seleccionar una acción existente (`acciones_pme`) | Requerido por el sistema |
| 2 | **Indicador (nombre)** | Nombre del indicador (ej: "Dominio de fracciones") | Libre, pero debe ser descriptivo |
| 3 | **Tipo de indicador** | `Cuantitativo` o `Cualitativo` | Determina cómo se mide luego en F-2 |
| 4 | **Asignatura asociada** | **Derivado automáticamente** del primer indicador de la acción (máximo 1 asignatura no "Transversal"). Si no hay acción, editable manualmente. | Se carga desde `definiciones_indicador.asignatura` |
| 5 | **Unidad de medida** | Ej: `%`, `puntos`, `escala 1-4` | Definido por usuario |
| 6 | **Línea base / Meta** | Valores inicial y objetivo | Numéricos |

### Ejemplo paso a paso (F-1)

```
Acción: "Refuerzo Matemático 2026"
→ Indicador: "Razonamiento lógico con fracciones"
→ Tipo: Cuantitativo
→ Asignatura asociada: Matemáticas (derivada de la acción)
→ Unidad: %
→ Línea base: 45% | Meta: 80%
```

**Nota técnica:** El campo `asignatura` se obtiene vía `/ingesta/indicadores_de_accion/{id}` y se muestra como `readonly` cuando hay acción seleccionada. Si se cambia la acción, el script vuelve a consultar y actualiza la asignatura.

---

## F-2 Parte 1: Carga de Notas y Asistencia (App Ponderado / RegistroAppPonderado)

**Objetivo:** Precargar datos de rendimiento académico del estudiante para la asignatura del taller.

### Flujo automático

1. **Seleccionar Acción / Taller (opcional)** → deriva asignatura.
2. **Seleccionar Estudiante** → activa carga de períodos disponibles.
3. **Seleccionar Período** → se carga dinámicamente mediante `/ingesta/periodos_estudiante?estudiante_id=X&asignatura=Y`.
4. **Precarga automática** → consulta `/ingesta/notas_estudiante` con `estudiante_id`, `periodo`, `asignatura`.

| Campo | Origen | Ejemplo | Estado tras precarga |
|---|---|---|---|
| Notas (promedio) | `RegistroAppPonderado`.promedio_notas (calculado) | `6,8` | Readonly (si existe registro) |
| % Asistencia | `RegistroAppPonderado`.porcentaje_asistencia | `92` | Readonly (si existe registro) |
| Asignatura | Derivada de la acción (o manual) | `Matemáticas` | Readonly cuando hay acción |

### Ejemplo de precarga (F-2 Parte 1)

```
Estudiante: Juan Pérez (id=12) — Curso: 8° Básico
Acción: Refuerzo Matemático 2026 → Asignatura: Matemáticas
Período seleccionado: 2026-03 (cargado dinámicamente de registros existentes)
→ Notas precargadas: 6,8
→ Asistencia precargada: 92%
```

**Si no hay registro previo:** Los campos quedan editables y muestran mensaje: *"Sin registro previo: puedes crear uno"*.

---

## F-2 Parte 2: Mediciones de Indicadores (Definiciones + Mediciones)

**Objetivo:** Medir el progreso del indicador definido en F-1 usando datos académicos y observación manual.

### Campos y orden de llenado

| Paso | Campo / Sección | Origen / Ejemplo | Dependencia |
|---|---|---|---|
| 1 | **Acción / Taller** | Selector (`med-accion-select`) | Requerido para cargar indicadores |
| 2 | **Estudiante** | Selector (`med-estudiante`) | Requerido para precargar notas |
| 3 | **Período** | Selector dinámico (`med-periodo`), mismo patrón que Parte 1: se llena con los periodos que tienen registro en `registros_app_ponderado` para el estudiante + asignatura, más dos opciones fijas de semestre | Se activa al elegir acción + estudiante |
| 4 | **Indicadores de la acción** | Cargados dinámicamente (`med-indicadores-container`) | Dependen de la acción |
| 5 | **Notas / Asistencia (referencia)** | **Precargado automático** (solo lectura) desde `RegistroAppPonderado`. Se deriva la asignatura de los indicadores cargados. | Se activa al seleccionar estudiante + período + acción |
| 6 | **Valor de la habilidad / competencia** | Manualmente ingresado por el docente (ej: 70% de cumplimiento) | Requerido para completar la medición |
| 7 | **Observaciones / Bitácora** | Texto libre justificador | Recomendado para trazabilidad |

### Ejemplo paso a paso (F-2 Parte 2 — Mediciones)

```
Acción: Refuerzo Matemático 2026
→ Indicadores cargados: "Razonamiento lógico con fracciones"
→ Estudiante: Ana López (id=5)
→ Período: 2026-08 (opción seleccionada del select dinámico; también ofrece
  "Promedio semestre 1 (2026-03 a 2026-06)" y "Promedio semestre 2 (2026-07 a 2026-10)")
→ Asignatura derivada: Matemáticas (del indicador cargado)
→ Precarga automática:
    Notas: 6,5 | Asistencia: 88% (2026-08 · Matemáticas) — solo lectura
→ Valor de la habilidad (manual): 75%
→ Observación: "Mejora notable en resolución de problemas con denominadores distintos."
```

### Opción "Promedio semestral"

Al elegir una de las opciones de semestre, el bloque de referencia muestra el
promedio de **todos los meses del rango fijo** que tengan registro para ese
estudiante en esa asignatura:

| Opción | Rango fijo | Valor guardado en `mediciones_indicador.periodo` |
|---|---|---|
| Promedio semestre 1 | `2026-03` a `2026-06` | `2026-S1` |
| Promedio semestre 2 | `2026-07` a `2026-10` | `2026-S2` |

Reglas del cálculo (endpoint `/ingesta/notas_periodos`):

- Los **meses sin registro se excluyen** del promedio (no se cuentan como 0).
- Se promedian los meses que sí tienen datos: **media simple de medias mensuales**
  (no distingue si un mes tuvo 1 o 3 evaluaciones).
- Si hay filas duplicadas para un mismo mes, gana la **más reciente**.
- El bloque informa además: `N de M meses con datos` y el rango `notas mín–máx`.

Ejemplo:

```
Estudiante: Ana López — Asignatura: Matemáticas
Período: Promedio semestre 1 (2026-03 a 2026-06)
→ Promedio semestre (2026-03 a 2026-06): 5.77 | Asistencia: 91.0%
  · 3 de 4 meses con datos · notas 4.5–6.0
  (2026-05 no tiene registro: se excluye del cálculo)
```

**Nota técnica:** el bloque `#med-notas-ref` se activa (`hidden` eliminado) cuando
hay resultado de `/ingesta/notas_periodos`. La precarga se dispara en el evento
`change` del select (no en `blur`), por lo que también se ejecuta al enviar el
formulario. Si no existe registro, muestra mensaje de ausencia de datos, pero
permite completar manualmente el valor de la habilidad.

---

## F-4: Registro de Participación en Talleres (ParticipacionAccion)

**Objetivo:** registrar las horas que un grupo de estudiantes asistió a un
taller en un período concreto y disparar el motor de cálculo.

### Campos

| Campo | Origen / Ejemplo | Dependencia |
|---|---|---|
| Acción / Taller | Selector (`acciones_pme`) | Requerido |
| **Periodo** | `<select>` fijo: meses del año de gestión (`2026-03` … `2026-10`) + `2026-S1` / `2026-S2` | Requerido; se guarda en `participaciones_accion.periodo` |
| Horas Aplicadas | Numérico, igual para todo el grupo | Requerido |
| Estudiantes | Multi-select | Requerido |

### Semántica del período

- **Mes (`2026-10`)** → las horas de esa carga pertenecen a octubre; se crea
  **una sola fila** `IndicadorAccion(mes="2026-10")` con las horas reales de
  ese mes.
- **Semestre (`2026-S2`)** → el motor **desglosa el semestre en sus meses**
  (`2026-07` … `2026-10`): las horas del semestre (más las filas sin período)
  se **reparten en partes iguales** entre los meses y se crea **una fila por
  mes**. Las horas que ya estuvieran registradas con un mes concreto del rango
  se suman a su mes (no se dividen).
  - *Por qué:* en la práctica muchos usuarios cargan el semestre de una vez;
    así la gráfica de Evolución Mensual muestra los meses aunque nadie
    registre mes a mes.
  - **Si el usuario registra mes a mes no cambia nada**: cada mes se procesa
    por separado con sus horas reales (comportamiento original).
  - El formulario F-4 muestra este aviso al elegir el período, y el
    mensaje de confirmación indica cuántos meses y cómo se repartieron.
- El motor (`_horas_por_estudiante(accion_id, periodo)`) **suma solo las horas
  de ese período**. Las filas antiguas sin período (`NULL`) siguen sumando en
  cualquier cálculo: son compatibles con los datos cargados antes de existir
  el campo.
- Al guardar se ejecuta `procesar_indicadores_accion(accion_id, periodo)`: con
  mes crea/actualiza una fila; con semestre crea una fila por cada mes del
  rango y **borra la fila agregada** del semestre.

> **Nota:** las mediciones semestrales de F-2 Parte 2 (`2026-S1/S2`) **sí se
> usan** al desglosar: si un mes no tiene medición propia, el motor toma la del
> semestre (`periodo_ref`). Igual en el flujo legacy: si el mes no tiene notas
> en App Ponderado se busca en el período del semestre.

---

## Vista de Detalle de Acción (`/acciones/detalle/<id>`)

**Objetivo:** analítica de una acción: estado, KPIs, gráficas de impacto y
cambio de estado.

### Componentes

| Zona | Contenido |
|---|---|
| KPIs (fila superior) | Alumnos, Horas totales, IEA, IPA, Progreso prom., Mejoraron, Meta Alcanzada y Retroceso (IPA en adelante, solo modelo nuevo) |
| Cabecera | Badge de estado coloreado + **formulario para cambiar el estado** (select + botón "Cambiar") + botón **"Recalcular"** |
| Analítica | Anillo de correlación de Pearson + barras de Proyección de Cumplimiento |
| **Evolución Mensual** (nueva) | Líneas de IPA y Progreso en % (eje izquierdo) e IEA en escala 0–5 (eje derecho), un punto por mes, desde `indicadores_accion` (`historico`). Incluye avisos del **origen de los datos**: reparto equitativo de un semestre, datos registrados mes a mes, o aviso de que el semestre aún está agregado (botón "Recalcular") |
| **Distribución de Alumnos** (nueva) | Doughnut + leyenda con conteos: modelo nuevo por `estado_grupal` (Meta alcanzada / En progreso / Sin cambio / Retroceso / Sin datos); modelo legacy por `clasificacion` de notas (Mejora alta / Mejora leve / Estable / Retroceso / Sin datos) |
| Impacto Individual | Scatter horas vs progreso/mejora + tabla con **una fila por alumno** (sin nombres repetidos), **filtro por habilidad** (`#impacto-ind-select`) que actualiza scatter y tabla a la vez, ordenado por horas descendente. Columnas: Alumno, Horas, Línea Base, Valor Actual, Progreso, Estado |
| Indicadores Afectados | Línea base, meta, IEA, semáforo y métricas IPA |

### Cambio de estado

- Formulario de la cabecera → `POST /acciones/cambiar_estado/<id>`.
- Estados válidos (`ESTADOS_ACCION` en `routes/acciones.py`): `Planificada`,
  `En Ejecución`, `Finalizada`, `Cancelada`.
- Estado no válido → flash de error y **no** se guarda; si es el mismo estado →
  mensaje informativo.
- El badge se recolorea según el estado (azul / cian / verde / rojo).
- **Ojo:** F-4 y el dashboard solo listan acciones `Planificada` o
  `En Ejecución`; al marcar `Finalizada`/`Cancelada` la acción sale de esos
  selectores.

### Recálculo de indicadores

- Botón **"Recalcular"** de la cabecera → `POST /acciones/recalcular/<id>`.
- Corre `procesar_indicadores_accion` para **cada período con horas**
  registradas (meses primero y semestres al final, para que el desglose del
  semestre sobrescriba con su reparto equitativo los meses ya calculados).
- Sirve para desglosar en meses un semestre cargado **sin duplicar horas** ni
  volver a pasar por F-4.
- Si no hay horas registradas → aviso; si no hay notas/mediciones → aviso.

### Estados vacíos

- Sin meses procesados → "Aún no hay meses procesados para esta acción" (cargar con F-4).
- Sin alumnos con horas → "Sin alumnos con horas registradas" (cargar con F-4).

---

## Relaciones clave entre formularios

- **F-1 → F-2 (Parte 2):** La acción seleccionada en F-1 define los indicadores; esos mismos indicadores se cargan en F-2 Parte 2 para medir.
- **F-2 (Parte 1) → F-2 (Parte 2):** El estudiante y la asignatura son consistentes entre ambas partes; en ambas el período es un select dinámico construido con los mismos endpoints.
- **F-2 (Parte 2) ↔ F-4:** Ambos usan el mismo catálogo de períodos (meses `YYYY-MM` + semestres `2026-S1/S2`). Al procesar un semestre el motor busca la medición del mes y, si no existe, usa la del semestre (`periodo_ref`), así que las mediciones semestrales de F-2 sí alimentan los meses desglosados.
- **F-4 → Detalle de Acción:** cada carga en F-4 crea/actualiza `IndicadorAccion`; si el período es un mes es una fila y si es un semestre es **una fila por mes** (reparto equitativo de horas). Eso alimenta la gráfica de Evolución Mensual; las horas registradas alimentan el scatter, la tabla y la distribución de alumnos.
- **App Ponderado (`registros_app_ponderado`) → F-2:** Provee los datos de notas y asistencia que se precargan automáticamente. Sin registro en esta tabla, F-2 muestra mensaje de ausencia pero sigue funcionando manualmente.

---

## Regla de oro para usuarios

1. Siempre defina primero la acción y sus indicadores en **F-1**.
2. Luego, si desea usar datos reales, registre o verifique los registros de **App Ponderado** (notas y asistencia) para el estudiante y período correspondientes.
3. En **F-2 Parte 1**, seleccione acción → estudiante → período para ver la precarga automática.
4. En **F-2 Parte 2**, seleccione la misma acción, el mismo estudiante y elija el período (o una opción de promedio semestral) para ver la referencia de notas, luego complete manualmente el valor de la habilidad.

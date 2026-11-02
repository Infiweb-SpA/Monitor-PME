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
| 3 | **Período** | Input de texto (`med-periodo`, ej: `2026-08`) | Requerido para consulta |
| 4 | **Indicadores de la acción** | Cargados dinámicamente (`med-indicadores-container`) | Dependen de la acción |
| 5 | **Notas / Asistencia (referencia)** | **Precargado automático** (solo lectura) desde `RegistroAppPonderado`. Se deriva la asignatura de los indicadores cargados. | Se activa al seleccionar estudiante + período + acción |
| 6 | **Valor de la habilidad / competencia** | Manualmente ingresado por el docente (ej: 70% de cumplimiento) | Requerido para completar la medición |
| 7 | **Observaciones / Bitácora** | Texto libre justificador | Recomendado para trazabilidad |

### Ejemplo paso a paso (F-2 Parte 2 — Mediciones)

```
Acción: Refuerzo Matemático 2026
→ Indicadores cargados: "Razonamiento lógico con fracciones"
→ Estudiante: Ana López (id=5)
→ Período: 2026-08 (escrito manualmente; no hay select dinámico aquí)
→ Asignatura derivada: Matemáticas (del indicador cargado)
→ Precarga automática:
    Notas: 6,5 | Asistencia: 88% (de RegistroAppPonderado, solo lectura)
→ Valor de la habilidad (manual): 75%
→ Observación: "Mejora notable en resolución de problemas con denominadores distintos."
```

**Nota técnica:** El bloque `#med-notas-ref` se activa (`hidden` eliminado) cuando hay resultado de `/ingesta/notas_estudiante`. Si no existe registro, muestra mensaje de ausencia de datos, pero permite completar manualmente el valor de la habilidad.

---

## Relaciones clave entre formularios

- **F-1 → F-2 (Parte 2):** La acción seleccionada en F-1 define los indicadores; esos mismos indicadores se cargan en F-2 Parte 2 para medir.
- **F-2 (Parte 1) → F-2 (Parte 2):** El estudiante y la asignatura son consistentes entre ambas partes, aunque en Parte 2 el período es manual.
- **App Ponderado (`registros_app_ponderado`) → F-2:** Provee los datos de notas y asistencia que se precargan automáticamente. Sin registro en esta tabla, F-2 muestra mensaje de ausencia pero sigue funcionando manualmente.

---

## Regla de oro para usuarios

1. Siempre defina primero la acción y sus indicadores en **F-1**.
2. Luego, si desea usar datos reales, registre o verifique los registros de **App Ponderado** (notas y asistencia) para el estudiante y período correspondientes.
3. En **F-2 Parte 1**, seleccione acción → estudiante → período para ver la precarga automática.
4. En **F-2 Parte 2**, seleccione la misma acción, el mismo estudiante y escriba el período para ver la referencia de notas, luego complete manualmente el valor de la habilidad.

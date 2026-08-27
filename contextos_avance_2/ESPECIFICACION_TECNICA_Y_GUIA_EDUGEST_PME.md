# ESPECIFICACIÓN TÉCNICA Y GUÍA DE IMPLEMENTACIÓN
## Evolución del motor de medición de impacto — EduGest PME

**Documento destinado a otra IA/developer junto con `CONTEXTO_SISTEMA.md`.**

---

## 0. INSTRUCCIÓN PRINCIPAL PARA LA IA

Lee primero `CONTEXTO_SISTEMA.md` y luego inspecciona el código real del proyecto antes de modificarlo.

Este documento define la evolución funcional y técnica requerida.

**No debes reconstruir el proyecto desde cero ni reemplazar funcionalidades existentes sin necesidad.**

El objetivo es evolucionar EduGest PME desde un sistema que mide principalmente notas/asistencia hacia un sistema capaz de medir:

- resultados académicos;
- asistencia;
- objetivos;
- habilidades;
- competencias;
- indicadores pedagógicos;
- rúbricas cuantificables;
- progreso hacia metas;
- relación entre participación y progreso.

Deben conservarse las funcionalidades existentes de:

- F-1;
- F-2;
- F-3;
- F-4;
- IEA;
- Pearson;
- proyección;
- semáforos;
- dashboard;
- reportes;
- exportaciones;
- auditoría.

La implementación debe ser incremental y compatible con acciones antiguas.

---

# 1. CONTEXTO REAL DEL PROYECTO

EduGest PME es una aplicación Flask que cruza:

```text
F-1 → definición de acciones PME
F-2 → resultados/evidencia de estudiantes por período
F-3 → datos SIGE oficiales
F-4 → participación de estudiantes en acciones
```

Actualmente, al guardar F-4 se ejecuta el motor y se generan:

```text
IEA
Pearson
Proyección
Semáforo
```

El contexto existente indica que el motor actual utiliza principalmente `indicador_tipo`, `unidad_medida`, `linea_base_valor` y `meta_valor`, y que Pearson relaciona horas de taller con variación de notas/asistencia.

**Esta especificación amplía ese modelo, no lo elimina.**

---

# 2. PROBLEMA PEDAGÓGICO A RESOLVER

Una acción PME no necesariamente tiene como resultado esperado una nota.

Ejemplo:

```text
Acción:
Taller de comprensión lectora

Objetivo:
Mejorar la lectura oral.

Indicador:
Velocidad lectora.

Unidad:
Palabras por minuto.

Línea base:
60 PPM.

Meta:
120 PPM.

Resultado actual:
95 PPM.
```

Decir solamente:

```text
95 < 120
→ NO CUMPLE
```

es insuficiente.

El estudiante pasó:

```text
60 → 95 → 120
```

Por lo tanto:

```text
Cambio absoluto = +35 PPM
```

y:

```text
Progreso hacia la meta =
(95 - 60) / (120 - 60)
= 58,3%
```

El sistema debe poder decir:

> La meta todavía no ha sido alcanzada, pero el estudiante ha recorrido el 58,3% de la brecha existente entre su línea base y la meta.

---

# 3. PRINCIPIO CENTRAL DEL NUEVO MOTOR

Separar cinco conceptos.

## 3.1 Resultado actual

Dónde se encuentra actualmente el estudiante.

```text
95 PPM
```

## 3.2 Delta

Cuánto cambió respecto de la línea base.

```text
95 - 60 = +35 PPM
```

## 3.3 Cumplimiento de meta

Qué tan cerca está del valor objetivo.

Debe calcularse respetando la dirección del indicador.

## 3.4 Progreso hacia la meta

Qué proporción de la brecha inicial ha recorrido.

```text
0% = línea base
100% = meta
<0% = retroceso
>100% = superación de meta
```

## 3.5 Relación participación-progreso

Qué relación existe entre:

```text
horas de participación
```

y:

```text
progreso hacia la meta
```

Esto será el nuevo uso generalizado de Pearson.

---

# 4. DIRECCIÓN DEL INDICADOR

Todo indicador debe tener una dirección:

```text
MAYOR_ES_MEJOR
MENOR_ES_MEJOR
```

## MAYOR_ES_MEJOR

Ejemplos:

- palabras por minuto;
- porcentaje de precisión;
- asistencia;
- porcentaje de logro;
- puntaje;
- rúbrica donde mayor puntuación representa mejor desempeño.

## MENOR_ES_MEJOR

Ejemplos:

- cantidad de errores;
- inasistencia;
- tiempo de resolución;
- cantidad de faltas;
- errores de lectura.

No asumir nunca que aumentar el valor significa mejorar.

---

# 5. FUNCIÓN PRINCIPAL DE PROGRESO

Crear una función pura similar a:

```python
calcular_progreso_indicador(
    linea_base,
    valor_actual,
    meta,
    direccion
)
```

Debe devolver información estructurada, como mínimo:

```python
{
    "delta": ...,
    "progreso_meta": ...,
    "cumplimiento": ...,
    "estado": ...
}
```

Se pueden agregar otros campos útiles.

---

# 6. FÓRMULA MAYOR_ES_MEJOR

Si:

```text
base = 60
actual = 95
meta = 120
```

usar:

```text
progreso =
(actual - base) / (meta - base)
```

Resultado:

```text
(95 - 60) / (120 - 60)
= 35 / 60
= 0,5833
= 58,3%
```

---

# 7. FÓRMULA MENOR_ES_MEJOR

Ejemplo:

```text
base = 15 errores
actual = 8 errores
meta = 5 errores
```

usar:

```text
progreso =
(base - actual) / (base - meta)
```

Resultado:

```text
(15 - 8) / (15 - 5)
= 7 / 10
= 70%
```

---

# 8. CASOS ESPECIALES

## 8.1 Retroceso

```text
base = 60
actual = 50
meta = 120
```

Debe producir:

```text
delta = -10
progreso = -16,7%
estado = RETROCESO
```

No ocultar retrocesos.

---

## 8.2 Sin cambio

```text
base = 60
actual = 60
meta = 120
```

Resultado:

```text
delta = 0
progreso = 0%
estado = ESTABLE
```

---

## 8.3 Superación de meta

```text
base = 60
actual = 130
meta = 120
```

Resultado:

```text
progreso > 100%
```

No recortar silenciosamente el valor matemático.

La interfaz puede limitar la barra visual a 100%, pero debe conservar el valor real.

---

## 8.4 Ya cumplía desde el inicio

```text
base = 130
meta = 120
actual = 135
```

El estudiante ya partía sobre la meta.

No debe producirse una interpretación absurda por un denominador negativo.

Usar un estado explícito:

```text
META_ALCANZADA
```

y conservar:

```text
delta = +5
cumplimiento = 112,5%
```

La metodología exacta para `progreso_meta` debe quedar documentada en el código.

---

## 8.5 Línea base igual a meta

```text
base == meta
```

No dividir por cero.

Usar:

```text
SIN_BRECHA
```

---

# 9. CUMPLIMIENTO Y PROGRESO NO SON LO MISMO

Esto es fundamental.

Para:

```text
base = 60
actual = 95
meta = 120
```

podemos tener:

```text
Cumplimiento respecto de meta:
95 / 120 = 79,2%
```

pero:

```text
Progreso desde la línea base:
(95 - 60) / (120 - 60)
= 58,3%
```

El sistema debe mostrar ambos cuando tenga sentido.

No utilizar únicamente:

```text
actual / meta
```

para determinar el progreso pedagógico.

Especialmente en indicadores `MENOR_ES_MEJOR`, ese cálculo puede ser engañoso.

---

# 10. NUEVO MODELO: ACCIÓN → INDICADORES

Actualmente `AccionPME` contiene campos como:

```text
indicador_tipo
unidad_medida
linea_base_valor
meta_valor
```

No eliminarlos inmediatamente.

Crear una estructura nueva que permita:

```text
AccionPME
    ↓
IndicadorAccion
```

Un `IndicadorAccion` debería poder contener conceptualmente:

```text
id
accion_id
nombre
descripcion
tipo
unidad_medida
direccion
linea_base
meta
peso
metodo_evaluacion
frecuencia_medicion
activo
```

Los nombres exactos deben adaptarse a las convenciones existentes del proyecto.

---

# 11. UNA ACCIÓN PUEDE TENER VARIOS INDICADORES

Ejemplo:

```text
Acción:
Taller de comprensión lectora

Objetivo:
Desarrollar lectura oral fluida y precisa.
```

Indicadores:

```text
1. Velocidad lectora
   Unidad: PPM
   Dirección: MAYOR_ES_MEJOR
   Base: 60
   Meta: 120
   Peso: 30%

2. Precisión lectora
   Unidad: %
   Dirección: MAYOR_ES_MEJOR
   Base: 75
   Meta: 95
   Peso: 50%

3. Errores de lectura
   Unidad: errores
   Dirección: MENOR_ES_MEJOR
   Base: 20
   Meta: 5
   Peso: 20%
```

Los pesos deben sumar 100% o ser normalizados por el motor.

---

# 12. TIPOS DE INDICADOR

El sistema debe dejar de depender exclusivamente de:

```text
Promedio Notas
Asistencia
```

Considerar al menos:

```text
NOTA
ASISTENCIA
HABILIDAD
COMPETENCIA
INDICADOR_PEDAGOGICO
RUBRICA
OTRO_CUANTITATIVO
```

No es obligatorio utilizar exactamente estos strings si el proyecto tiene otra convención.

---

# 13. COMPETENCIAS Y HABILIDADES

Una competencia cualitativa no debe convertirse directamente en una fórmula.

Ejemplo incorrecto:

```text
Pensamiento crítico = "Sí/No"
```

Mejor:

```text
Pensamiento crítico

Argumentación: 1–4
Uso de evidencia: 1–4
Análisis: 1–4
Conclusión: 1–4
```

Cada dimensión de la rúbrica puede convertirse en indicador cuantificable.

Así el motor puede calcular progreso.

---

# 14. NUEVA ENTIDAD: MEDICIÓN DE INDICADOR

Crear una entidad equivalente a:

```text
MedicionIndicador
```

Conceptualmente:

```text
id
estudiante_id
indicador_id
periodo
valor
observacion
```

Esto permitirá:

```text
Juan Pérez
Velocidad lectora
2026-08
95
```

y:

```text
Juan Pérez
Precisión
2026-08
91
```

y:

```text
Juan Pérez
Errores
2026-08
8
```

---

# 15. F-1: EVOLUCIÓN NECESARIA

F-1 debe continuar permitiendo crear una acción PME.

Agregar la posibilidad de definir:

```text
Objetivo de la acción
```

y:

```text
Indicadores de evaluación
```

Cada indicador debe permitir:

```text
Nombre
Descripción
Tipo
Unidad
Dirección
Línea base
Meta
Peso
Método de evaluación
Frecuencia
```

La interfaz debe permitir:

```text
+ Agregar indicador
```

y eliminar indicadores antes de guardar.

Debe ser posible crear:

```text
1 indicador
2 indicadores
3 indicadores
...
```

---

# 16. F-2: EVOLUCIÓN NECESARIA

Actualmente F-2 contiene datos académicos por estudiante/período/asignatura.

Eso debe seguir funcionando.

Pero F-2 debe poder almacenar también:

```text
mediciones de indicadores pedagógicos
```

Conceptualmente:

```text
Estudiante
Período
Indicador
Valor
Observación
```

La intención es que F-2 pase conceptualmente de:

```text
"registro de notas"
```

a:

```text
"evidencia de resultados del estudiante"
```

sin perder notas ni asistencia.

---

# 17. F-4: NO ROMPER

F-4 debe seguir almacenando:

```text
estudiante
acción
horas_asistencia
asistencia_talleres
fecha_registro
```

Las horas deben continuar acumulándose cuando corresponda.

La novedad es que ahora esas horas se relacionarán con:

```text
progreso del indicador
```

en vez de limitarse a:

```text
delta de nota
```

---

# 18. NUEVO PEARSON

No eliminar Pearson.

Generalizarlo.

Antes:

```text
X = horas
Y = delta de nota/asistencia
```

Ahora debe poder utilizar:

```text
X = horas de participación
Y = progreso hacia la meta
```

Ejemplo:

```text
Alumno A → 5 horas → 10% progreso
Alumno B → 10 horas → 20%
Alumno C → 20 horas → 42%
Alumno D → 30 horas → 60%
Alumno E → 40 horas → 75%
```

Calcular:

```python
pearson(horas, progreso)
```

Interpretar como asociación, nunca causalidad.

Texto recomendado:

> Se observa una asociación positiva entre la participación en la acción y el progreso del indicador.

No utilizar:

> El taller causó el 71% de la mejora.

---

# 19. PEARSON Y MUESTRAS PEQUEÑAS

Conservar la protección existente:

```text
n < 2 → no calcular
```

Además:

```text
n = 2
```

puede producir matemáticamente:

```text
r = +1 o -1
```

porque dos puntos forman una línea perfecta.

Cuando:

```text
n < 5
```

mostrar una advertencia de muestra pequeña.

No afirmar significancia estadística si no se ha calculado.

---

# 20. NUEVA MÉTRICA: IPA

Crear una métrica agregada provisional:

```text
IPA = Índice de Progreso de la Acción
```

Representa el progreso promedio de la acción hacia sus objetivos.

Si existen múltiples indicadores:

```text
Velocidad = 58%
Precisión = 80%
Errores = 70%
```

con pesos:

```text
30%
50%
20%
```

calcular:

```text
IPA =
58 × 0,30 +
80 × 0,50 +
70 × 0,20

= 71,4%
```

Normalizar pesos si fuera necesario.

El nombre IPA es provisional y puede cambiar posteriormente.

---

# 21. MÉTRICAS INDIVIDUALES

Para cada estudiante/indicador mostrar:

```text
Línea base
Valor actual
Meta
Delta
Cumplimiento
Progreso hacia meta
Estado
Horas de participación
```

Ejemplo:

```text
Juan Pérez

Velocidad lectora

Base: 60 PPM
Actual: 95 PPM
Meta: 120 PPM

Cambio: +35 PPM
Cumplimiento: 79,2%
Progreso: 58,3%

Estado: EN PROGRESO

Horas: 20
```

---

# 22. ESTADOS

Generalizar las clasificaciones existentes para que no dependan exclusivamente de notas.

Estados posibles:

```text
META_ALCANZADA
MEJORA_ALTA
MEJORA_LEVE
ESTABLE
RETROCESO
SIN_DATOS
SIN_BRECHA
```

Los umbrales deben ser configurables cuando sea razonable.

No eliminar las clasificaciones existentes hasta comprobar compatibilidad.

---

# 23. MÉTRICAS A NIVEL DE ACCIÓN

Por cada acción calcular, cuando haya datos:

```text
IPA
Delta promedio
Progreso promedio
Cumplimiento promedio
% estudiantes que mejoraron
% estudiantes que alcanzaron meta
% estudiantes en retroceso
Pearson horas vs progreso
Proyección
Semáforo
IEA
```

Ejemplo:

```text
Taller de comprensión lectora

IPA: 67%
Cambio promedio: +31 PPM
Estudiantes que mejoraron: 82%
Estudiantes que alcanzaron meta: 34%
Estudiantes en retroceso: 8%
Pearson: +0,71
Proyección: 91%
Semáforo: Amarillo
```

---

# 24. NIVEL OBJETIVO PME

Permitir agregar resultados por `ObjetivoPME`.

Ejemplo:

```text
Objetivo:
Fortalecer habilidades de comprensión lectora

Acción 1 → 72%
Acción 2 → 81%
Acción 3 → 64%

Progreso objetivo → 72,3%
```

La ponderación debe ser consistente y documentada.

---

# 25. NIVEL DIMENSIÓN PME

El sistema ya posee las cuatro dimensiones:

```text
Gestión Pedagógica
Liderazgo Escolar
Convivencia Escolar
Gestión de Recursos
```

Mantenerlas.

Permitir calcular:

```text
progreso por dimensión
```

agregando los objetivos/acciones correspondientes.

---

# 26. NIVEL ESTABLECIMIENTO

Crear posteriormente un indicador institucional, por ejemplo:

```text
Índice de Progreso PME
```

Ejemplo:

```text
Gestión Pedagógica       81%
Liderazgo Escolar        74%
Convivencia Escolar      88%
Gestión de Recursos      91%

Progreso PME             83%
```

La metodología debe ser explícita.

No mezclar arbitrariamente:

```text
progreso pedagógico
Pearson
IEA
ejecución presupuestaria
```

Son conceptos distintos.

---

# 27. IEA

Mantener el IEA existente.

El contexto actual indica que el IEA considera:

- impacto pedagógico normalizado;
- recurso invertido;
- horas;
- presupuesto;
- penalización por sobregiro;
- pesos configurables.

La evolución debe permitir que el componente de impacto pedagógico pueda aprovechar el nuevo concepto de progreso.

Antes de modificar `calcular_iea()`:

1. inspeccionar su implementación;
2. identificar todos sus consumidores;
3. identificar cómo se interpreta actualmente;
4. modificar solo lo necesario;
5. ejecutar pruebas con el escenario existente.

No eliminar:

```text
peso_rendimiento
peso_asistencia
presupuesto
sobregiro
```

---

# 28. PROYECCIÓN

Mantener:

```text
serie por período
→ regresión lineal
→ proyección a noviembre
→ comparación con meta
→ semáforo
```

Generalizarla para indicadores distintos de notas.

Ejemplo:

```text
PPM:
60
70
80
95

Meta:
120
```

Debe poder proyectar el valor esperado en noviembre.

La dirección del indicador debe ser respetada.

Para:

```text
MENOR_ES_MEJOR
```

una disminución debe interpretarse como mejora.

---

# 29. SEMÁFOROS

Separar:

## Semáforo de proyección

Responde:

> ¿Se proyecta que la acción alcance su meta?

Mantener la lógica existente de:

```text
Verde
Amarillo
Rojo
```

según configuración.

## Estado de progreso

Responde:

> ¿Los estudiantes están mejorando?

Puede considerar:

```text
Verde → progreso adecuado
Amarillo → progreso insuficiente
Rojo → retroceso
```

No fusionar ambos conceptos.

---

# 30. DASHBOARD

Mantener los KPIs actuales.

Agregar progresivamente:

```text
Progreso PME
Progreso por dimensión
Progreso por objetivo
Acciones con mayor progreso
Acciones con retroceso
% estudiantes que alcanzaron meta
Pearson participación/progreso
```

No mostrar datos nuevos si no existen.

---

# 31. DETALLE DE ACCIÓN

La vista debe mostrar:

```text
Objetivo
Indicadores
Línea base
Meta
Resultado actual
Delta
Progreso
Cumplimiento
IPA
Pearson
Proyección
Semáforo
IEA
```

Para múltiples indicadores:

```text
Indicador             Progreso
--------------------------------
Velocidad lectora       58%
Precisión               80%
Errores                 70%
--------------------------------
IPA                     71,4%
```

Mantener:

- información presupuestaria;
- gasto;
- sobregiro;
- tabla individual;
- scatter plot.

---

# 32. SCATTER PLOT

El gráfico debe poder utilizar:

```text
X = horas de participación
Y = progreso hacia meta
```

Si existen varios indicadores, permitir seleccionar uno.

Ejemplo:

```text
Indicador:
[Velocidad lectora ▼]
```

---

# 33. REPORTES

Mantener reportes actuales.

Cuando existan indicadores nuevos, incluir:

```text
Acción
Objetivo
Indicador
Línea base
Meta
Valor actual
Delta
Progreso
Cumplimiento
IPA
Pearson
Proyección
Semáforo
```

Mantener:

- Excel;
- HTML/PDF imprimible;
- ZIP de auditoría;
- filtros.

---

# 34. NORMALIZACIÓN

No comparar directamente:

```text
PPM
%
errores
notas 1–7
rúbrica 1–4
```

Para agregaciones utilizar:

```text
progreso normalizado hacia meta
```

donde:

```text
0 = línea base
1 = meta
```

Esto permite crear indicadores compuestos.

---

# 35. COMPATIBILIDAD LEGACY

Este requisito es obligatorio.

El sistema tiene acciones existentes que utilizan:

```text
indicador_tipo
unidad_medida
linea_base_valor
meta_valor
```

No todas tendrán `IndicadorAccion`.

El motor debe soportar:

## Modelo antiguo

```text
AccionPME
    ├── indicador_tipo
    ├── unidad_medida
    ├── linea_base_valor
    └── meta_valor
```

## Modelo nuevo

```text
AccionPME
    ↓
IndicadorAccion
    ↓
MedicionIndicador
```

Regla:

> Si existe configuración nueva, usarla. Si no existe, mantener el comportamiento legacy.

---

# 36. BASE DE DATOS

El contexto indica que el proyecto usa SQLite.

También indica que:

```text
db.create_all()
```

no modifica tablas existentes.

Por tanto:

**No borrar automáticamente `edugest_pme.db`.**

Toda modificación de modelos debe preservar datos.

La IA debe:

1. inspeccionar el esquema actual;
2. determinar qué tablas nuevas hacen falta;
3. determinar qué columnas nuevas hacen falta;
4. crear una estrategia de migración;
5. preservar datos existentes;
6. documentar cómo actualizar una instalación existente.

Si se utiliza Flask-Migrate/Alembic, preferir migraciones.

Si no existe una estrategia de migración adecuada, crearla de manera compatible con el proyecto.

---

# 37. ORDEN DE IMPLEMENTACIÓN

No implementar todo simultáneamente.

Seguir este orden:

```text
1. Inspeccionar código real
2. Inspeccionar modelos actuales
3. Inspeccionar pme_engine.py
4. Inspeccionar rutas F-1/F-2/F-4
5. Inspeccionar templates
6. Crear calcular_progreso_indicador()
7. Crear pruebas unitarias
8. Crear IndicadorAccion
9. Crear MedicionIndicador
10. Implementar migración
11. Implementar compatibilidad legacy
12. Modificar F-1
13. Modificar F-2
14. Generalizar motor
15. Generalizar Pearson
16. Adaptar proyección
17. Crear IPA
18. Adaptar detalle de acción
19. Adaptar dashboard
20. Adaptar reportes
21. Agregar agregación por objetivo
22. Agregar agregación por dimensión
23. Agregar indicador institucional
24. Ejecutar pruebas completas
25. Probar con datos legacy
26. Probar con datos nuevos
```

---

# 38. PRUEBAS UNITARIAS OBLIGATORIAS

## Mayor es mejor

```text
base=60
actual=95
meta=120

progreso ≈ 0.5833
```

## Menor es mejor

```text
base=15
actual=8
meta=5

progreso = 0.70
```

## Sin cambio

```text
base=60
actual=60
meta=120

progreso=0
```

## Retroceso

```text
base=60
actual=50
meta=120

progreso<0
```

## Superación

```text
base=60
actual=130
meta=120

progreso>1
```

## Meta alcanzada desde base

```text
base=130
actual=135
meta=120

no debe producir error
estado META_ALCANZADA
```

## Base igual a meta

```text
base=120
actual=120
meta=120

estado SIN_BRECHA
```

## Pearson sin muestra suficiente

```text
n<2
→ None
```

## Pearson con 2 observaciones

Verificar el resultado matemático y mostrar advertencia.

## Pesos

Verificar:

```text
30 + 50 + 20 = 100
```

y que el motor también funcione si recibe pesos que requieren normalización.

## Legacy

Verificar que una acción antigua siga produciendo:

```text
IEA
Pearson
Proyección
Semáforo
```

---

# 39. CASO DE PRUEBA COMPLETO

Crear un escenario similar a:

```text
Acción:
Taller de comprensión lectora
```

Indicador:

```text
Velocidad lectora
Base: 60
Meta: 120
Dirección: MAYOR_ES_MEJOR
```

Estudiantes:

```text
Alumno A:
Base 60
Actual 95
Horas 20

Alumno B:
Base 80
Actual 110
Horas 30

Alumno C:
Base 100
Actual 115
Horas 35
```

Resultados esperados:

```text
A:
Delta +35
Progreso 58,3%

B:
Delta +30
Progreso 75%

C:
Delta +15
Progreso 75%
```

Luego:

```text
Pearson(
    horas=[20,30,35],
    progreso=[58.3,75,75]
)
```

El valor exacto debe calcularlo el programa, no inventarlo.

---

# 40. EJEMPLO CON MÚLTIPLES INDICADORES

Acción:

```text
Taller de lectura
```

Indicadores:

```text
Velocidad:
Base 60
Actual 95
Meta 120
Peso 30%

Precisión:
Base 75
Actual 91
Meta 95
Peso 50%

Errores:
Base 20
Actual 8
Meta 5
Peso 20%
```

Calcular individualmente:

```text
progreso velocidad
progreso precisión
progreso errores
```

Después:

```text
IPA =
progreso_velocidad * 0.30
+
progreso_precision * 0.50
+
progreso_errores * 0.20
```

---

# 41. REGLAS ESTADÍSTICAS

No presentar Pearson como causalidad.

No decir:

```text
"El taller produjo la mejora."
```

si solamente se tiene correlación.

Usar:

```text
"Se observa asociación entre participación y progreso."
```

Además:

- indicar tamaño de muestra;
- advertir muestras pequeñas;
- evitar conclusiones causales;
- no inventar significancia;
- conservar el valor matemático real.

---

# 42. REGLAS DE INTERFAZ

La interfaz debe hacer comprensible el análisis a un director/sostenedor sin conocimientos estadísticos.

Preferir:

```text
Progreso hacia meta: 58,3%
```

sobre mostrar solamente:

```text
0,5833
```

Para Pearson:

```text
r = +0,71
Asociación positiva
```

y una explicación breve.

Para retroceso:

```text
Retroceso
```

debe ser visible.

Para meta no alcanzada pero progreso positivo:

```text
Meta pendiente
Progreso: 58,3%
```

No mostrar solamente:

```text
NO CUMPLE
```

---

# 43. INFORMACIÓN QUE DEBE PODER RESPONDER EL SISTEMA

## Resultado

```text
¿Los estudiantes mejoraron?
```

→ Delta.

## Progreso

```text
¿Cuánto avanzaron hacia la meta?
```

→ Progreso normalizado.

## Meta

```text
¿Cuántos alcanzaron el objetivo?
```

→ Tasa de cumplimiento.

## Acción

```text
¿Cómo está funcionando la acción?
```

→ IPA.

## Participación

```text
¿La participación está asociada al progreso?
```

→ Pearson.

## Proyección

```text
¿Llegará a la meta?
```

→ Proyección.

## Recursos

```text
¿Fue eficiente la inversión?
```

→ IEA.

## PME

```text
¿Cómo está creciendo el establecimiento?
```

→ agregación:

```text
acción
→ objetivo
→ dimensión
→ establecimiento
```

---

# 44. RESULTADO COMERCIAL ESPERADO

El sistema debe ser capaz de generar una conclusión como:

> El taller de comprensión lectora aún no alcanza la meta de 120 palabras por minuto. Sin embargo, el promedio de los estudiantes aumentó desde 60 hasta 95 PPM, recorriendo el 58,3% de la brecha hacia la meta. El 82% de los estudiantes presentó mejora y se observa una asociación positiva entre las horas de participación y el progreso.

Esto representa mejor el impacto pedagógico que decir solamente:

> La meta no se cumplió.

---

# 45. DEFINICIÓN CONCEPTUAL FINAL

La evolución del producto debe pasar de:

```text
"¿Subieron las notas?"
```

a:

```text
"¿Los estudiantes están avanzando hacia los objetivos definidos?"
```

Y después:

```text
"¿Ese avance está relacionado con su participación en las acciones?"
```

Y finalmente:

```text
"¿El establecimiento está progresando en los objetivos y dimensiones de su PME?"
```

La arquitectura final deseada es:

```text
                         F-1
                          │
                    ACCIÓN PME
                          │
                    OBJETIVO ACCIÓN
                          │
                 ┌────────┴────────┐
                 │                 │
            INDICADOR 1       INDICADOR 2...
                 │
          línea base / meta
                 │
                 ▼
                 F-2
                 │
            MEDICIONES
                 │
                 ▼
                 F-4
                 │
            PARTICIPACIÓN
                 │
                 ▼
          MOTOR DE EVALUACIÓN
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
     Delta    Progreso    Meta
       │         │         │
       └─────────┼─────────┘
                 │
          ┌──────┴───────┐
          ▼              ▼
       Pearson          IEA
          │
          ▼
      Proyección
          │
          ▼
       Semáforo
          │
          ▼
    RESULTADO ACCIÓN
          │
     ┌────┴────┐
     ▼         ▼
 Objetivo   Dimensión
     │         │
     └────┬────┘
          ▼
     PROGRESO PME
```

---

# 46. INSTRUCCIÓN OPERATIVA PARA LA IA

Antes de escribir código:

1. Lee `CONTEXTO_SISTEMA.md`.
2. Inspecciona los archivos reales.
3. Identifica qué partes ya están implementadas.
4. No asumas nombres de clases o columnas si no aparecen en el código.
5. Diseña la migración antes de modificar modelos.
6. Implementa primero la función matemática.
7. Crea pruebas.
8. Después modifica modelos.
9. Después modifica formularios/rutas.
10. Finalmente modifica dashboard y reportes.

Después de cada etapa:

```text
- ejecutar tests;
- revisar errores;
- comprobar compatibilidad;
- verificar datos existentes.
```

No hacer cambios masivos sin explicar qué archivos se modificarán.

---

# 47. FORMATO DE RESPUESTA ESPERADO DE LA IA QUE IMPLEMENTE

Antes de modificar el proyecto, debe entregar:

```text
1. Diagnóstico del código actual.
2. Archivos que necesitan modificación.
3. Archivos que necesitan creación.
4. Cambios de base de datos.
5. Estrategia de compatibilidad legacy.
6. Fórmulas que se implementarán.
7. Plan de implementación por etapas.
```

Después de implementar:

```text
1. Archivos modificados.
2. Archivos creados.
3. Cambios de BD.
4. Nuevas funciones.
5. Nuevos modelos.
6. Cambios F-1.
7. Cambios F-2.
8. Cambios F-4.
9. Cambios Pearson.
10. Cambios IEA.
11. Cambios proyección.
12. Tests ejecutados.
13. Resultados de tests.
14. Posibles pendientes.
```

No afirmar que algo funciona si no fue probado.

---

# 48. CRITERIO DE TERMINADO

La evolución se considera funcional cuando:

- una acción antigua sigue funcionando;
- una acción nueva puede tener indicadores;
- un indicador puede tener dirección;
- se puede registrar una medición por estudiante/período;
- el motor calcula delta;
- el motor calcula progreso;
- el motor identifica retroceso;
- el motor identifica meta alcanzada;
- el motor maneja menor-es-mejor;
- Pearson puede relacionar horas con progreso;
- el IPA puede agregarse;
- la proyección funciona con indicadores nuevos;
- IEA continúa funcionando;
- dashboard funciona;
- reportes funcionan;
- exportaciones funcionan;
- no se pierden datos existentes;
- existen pruebas automatizadas para los casos críticos.

---

# 49. REGLA FINAL

**No sacrificar la integridad estadística por una métrica comercial bonita.**

EduGest PME debe ser capaz de presentar resultados fáciles de entender, pero los cálculos deben conservar su significado matemático.

El sistema debe diferenciar siempre:

```text
CAMBIO
PROGRESO
CUMPLIMIENTO
ASOCIACIÓN
PROYECCIÓN
EFICIENCIA
```

Son conceptos diferentes.

La gran propuesta de valor del nuevo motor es:

> **Medir cuánto avanzan los estudiantes y establecimientos hacia objetivos pedagógicos concretos, y relacionar ese progreso con la participación y los recursos utilizados en las acciones del PME.**

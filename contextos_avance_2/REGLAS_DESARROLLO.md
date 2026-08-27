¡Muy buena práctica! Tener reglas de tamaño explícitas evita que el proyecto se vuelva inmantenible a medida que crece (y ya tenemos algunos archivos que rozan los límites). 

Aquí tienes el documento, con límites **justificados por tipo de archivo** y estrategias de división específicas para TU arquitectura (no reglas genéricas):

### Archivo: `contexto_avance_2/03-REGLAS_DESARROLLO.md`

# REGLAS DE DESARROLLO — Límites de Tamaño y Estructura
## EduGest PME

> **Propósito**: Mantener el código legible, revisable y mantenible a medida que el producto
> escala. Un archivo que excede su límite es una señal de que debe dividirse, no de que la regla
> debe relajarse.
>
> **Cómo leer los límites**: Son máximos ALTO (hard limits para py, soft limits con tolerancia
> del 15% para html). Superarlos requiere justificación documentada (ver §6).

---

## 1. FILOSOFÍA GENERAL

1. **Cada archivo debe poder explicarse en una frase**: "este archivo gestiona X".
   Si necesitas dos frases, son dos archivos.
2. **Los templates pesan más que el Python**: en este proyecto la lógica crítica está en
   `pme_engine.py`; un error de UI no rompe los cálculos, pero un archivo de 800 líneas
   sí rompe la capacidad de modificar la UI sin miedo.
3. **Dividir por responsabilidad, no por tamaño a la fuerza**: extraer código a un archivo
   nuevo solo si tiene una razón de ser propia (un partial, un service, un helper).
4. Regla de oro para IA/desarrolladores nuevos: **si agregas funcionalidad y el archivo
   supera el límite, la tarea incluye el refactor** — no se delega "para después".

---

## 2. LÍMITES: ARCHIVOS PYTHON (.py)

| Tipo de archivo | Límite | Justificación |
|---|---|---|
| `run.py`, `app/extensions.py` | **50 líneas** | Archivos de arranque/registro: deben ser triviales. |
| `app/config.py` | **100 líneas** | Solo clases de configuración por entorno. |
| `app/__init__.py` (factory) | **120 líneas** | Factory + registro de blueprints + filtros Jinja. Si crece, mover filtros a `app/jinja_filters.py`. |
| `app/models/*.py` | **250 líneas** | Un dominio por archivo (pme, metrics, user). Si crece: separar modelos por sub-dominio (ej. `models/pme_acciones.py`). |
| `app/routes/*.py` (blueprints) | **300 líneas** | Un módulo de negocio por blueprint. Si crece: extraer lógica a services o dividir el blueprint. |
| `app/services/*.py` | **400 líneas** | El motor algorítmico es denso pero cohesivo. Si crece: separar motor (matemática pura) de orquestadores (consultas BD). |
| `seed.py` y scripts raíz | **350 líneas** | Scripts de una sola corrida. Si crece: dividir en `scripts/seed_*.py` por dominio. |
| Tests (`tests/*.py`) | Sin límite de archivo | Pero cada test ≤ 30 líneas. |

### 2.1 Límites internos de Python

| Elemento | Límite | Notas |
|---|---|---|
| Función / método | **50 líneas** | `procesar_indicadores_accion` ronda el tope: si crece más, extraer helpers. |
| Clase (modelo SQLAlchemy) | **80 líneas** | Incluye docstrings y `__repr__`. |
| Lista/diccionario literal | **40 líneas** | (Como `ACCIONES_DATA` del seed: extraer a módulo de datos si crece). |
| Imports | **20 líneas** | Si hay más, el archivo probablemente hace demasiado. |
| Línea individual | **100 caracteres** | Configurar en el editor (ruler en VS Code). |

---

## 3. LÍMITES: TEMPLATES HTML (.html / Jinja2)

| Tipo de template | Límite | Justificación |
|---|---|---|
| `layouts/base.html` | **150 líneas** | Estructura + sidebar + flash messages. Nada más. |
| Templates simples (login, index de listado) | **200 líneas** | Un propósito único por pantalla. |
| Templates complejos (detalle, configuración con tabs) | **400 líneas** | Tope con tolerancia: hasta 460 (15%) si es irreducible. |
| Partials `_*.html` | **150 líneas** | Fragmentos reutilizables extraídos de templates grandes. |
| Macros `_macros.html` | **200 líneas** | Componentes repetidos (badges, tablas, cards KPI). |
| Documentos imprimibles (`reportes/ejecutivo.html`) | **300 líneas** | HTML autocontenido + CSS inline de impresión. |

### 3.1 Límites internos de templates

| Elemento | Límite | Notas |
|---|---|---|
| Bloque `<form>` | **150 líneas** | Un formulario largo (como F-1) que crezca → mover a partial `_form_f1.html`. |
| Bloque `<script>` inline | **80 líneas** | Si el JS crece más, mover a `app/static/js/<modulo>.js`. |
| Tabla HTML | **60 líneas** | Si crece, revisar columnas o usar macro de tabla. |
| Indentación máxima | **6 niveles** | Más de 6 → reestructurar con grid en lugar de anidar divs. |

---

## 4. ESTRATEGIAS DE DIVISIÓN (específicas de este proyecto)

### 4.1 Cuando un template HTML excede el límite
1. **Tabs → Partials**: un template con tabs (ingesta, configuración) debe extraer cada tab
   a `templates/<modulo>/partials/_tab1_formulario.html`, dejando el archivo principal solo
   con la navegación y los `{% include %}`.
2. **Componentes repetidos → Macros**: los badges de semáforo aparecen en dashboard, detalle
   de acción, reportes y ejecutivo. Crear `templates/macros/_badges.html`:
   ```jinja
   {% macro badge_semaforo(estado, pequeño=false) %}...{% endmacro %}
   ```
   Lo mismo aplica a: cards KPI, tablas de acciones, barras de presupuesto.
3. **JS inline → archivo estático**: cuando un `<script>` pase de 80 líneas, moverlo a
   `app/static/js/` y referenciarlo con `{{ url_for('static', filename='js/x.js') }}`.
   Los datos dinámicos se inyectan con un pequeño script puente o `data-*` attributes.

### 4.2 Cuando un blueprint (.py) excede el límite
1. **Lógica de negocio → Services**: las rutas solo orquestan (leer request, llamar service,
   responder). Ejemplo: si `reportes.py` creciera, mover la construcción de DataFrames a
   `app/services/report_builder.py`.
2. **Dividir blueprint**: si un módulo tiene dos sub-dominios claros (ej. acciones CRUD vs
   acciones importación Excel), dividir en `acciones.py` y `acciones_excel.py` registrando
   ambos sobre el mismo `url_prefix`.
3. **Helpers compartidos → utils**: funciones como `parse_date()` usadas por varios módulos
   van a `app/utils.py` (≤ 150 líneas).

### 4.3 Cuando el motor (services) excede el límite
Separar siempre en dos capas:
- `pme_engine.py`: SOLO matemática pura (funciones sin consultas a BD). Testeable aislada.
- Orquestadores y helpers de consulta: pueden ir a `pme_orchestrator.py` si el archivo crece.

---

## 5. REGLAS COMPLEMENTARIAS DE ESTRUCTURA

1. **Docstrings obligatorios**: toda función pública de services y rutas POST lleva docstring
   de una línea mínimo (patrón ya usado en todo el proyecto — mantenerlo).
2. **Nomenclatura**: rutas con `snake_case`, templates en espejo de la ruta
   (`ingesta/index.html` ↔ `ingesta.index`), partials con prefijo `_`.
3. **Un blueprint = un template folder**: mantener el `template_folder` declarado por blueprint.
4. **No mezclar idiomas**: código y comentarios en español (idioma del proyecto), nombres de
   variables en español o inglés pero consistente dentro de cada archivo.

---

## 6. EXCEPCIONES (cómo documentarlas)

Si un archivo DEBE exceder su límite (ej. tabla de datos oficiales, formulario regulatorio
irreducible), agregar este comentario al inicio del archivo:

```python
# [EXCEPCION-REGLAS] Excede el límite de líneas (motivo: ...).
# Aprobado en fecha: ... | Revisar en: ...
```

Máximo 3 excepciones activas en todo el proyecto. Si hay 4, es una refactorización pendiente,
no 4 excepciones.

---

## 7. AUDITORÍA DEL ESTADO ACTUAL (Avance 2)

⚠️ Estados estimados — verificar con el script del §8:

| Archivo | Línea base aprox. | Estado | Acción sugerida |
|---|---|---|---|
| `routes/acciones.py` | ~250 | ✅ OK | Vigilar: la lógica Excel podría migrar a service si crece. |
| `routes/reportes.py` | ~280 | ⚠️ Cerca del tope | Si se agregan más reportes → extraer `services/report_builder.py`. |
| `routes/config.py` | ~180 | ✅ OK | — |
| `routes/ingesta.py` | ~130 | ✅ OK | — |
| `services/pme_engine.py` | ~330 | ⚠️ Cerca del tope | Próximo growth → dividir motor/orquestador (§4.3). |
| `seed.py` | ~300 | ⚠️ Cerca del tope | Si se agregan más datos → `scripts/seed_*.py`. |
| `templates/ingesta/index.html` | ~500 | 🔴 EXCEDE | **Prioridad**: extraer tabs a partials (§4.1). |
| `templates/configuracion/index.html` | ~450 | 🔴 EXCEDE (en tolerancia) | Extraer tabs a partials. |
| `templates/acciones/detalle.html` | ~400 | ⚠️ En el tope | Extraer sección "Impacto Individual" a partial. |
| `templates/reportes/ejecutivo.html` | ~200 | ✅ OK | — |
| `templates/dashboard/index.html` | ~250 | ✅ OK | — |

**Deuda técnica de estructura aceptada para el Avance 2**: los 3 templates marcados en rojo.
Primer refactor de estructura propuesto: partials de ingesta (backlog general).

---

## 8. SCRIPT DE AUDITORÍA AUTOMÁTICA

Guardar como `auditar_lineas.py` en la raíz y ejecutar `python auditar_lineas.py`:

```python
#!/usr/bin/env python3
"""Audita el cumplimiento de las reglas de líneas por archivo."""
import os

LIMITES = {
    ".py": [("routes", 300), ("services", 400), ("models", 250), ("__init__.py", 120)],
    ".html": [("partials", 150), ("macros", 200), ("ejecutivo", 300)],
}
DEFAULT_PY, DEFAULT_HTML = 350, 400  # defaults: scripts raíz / templates normales

raiz = os.path.dirname(os.path.abspath(__file__))
violaciones = 0

for carpeta, _, archivos in os.walk(raiz):
    if any(x in carpeta for x in ["__pycache__", ".git", "instance", "node_modules"]):
        continue
    for arch in archivos:
        ext = os.path.splitext(arch)[1]
        if ext not in (".py", ".html"):
            continue
        ruta = os.path.join(carpeta, arch)
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            n = sum(1 for _ in f)
        limite = DEFAULT_PY if ext == ".py" else DEFAULT_HTML
        for clave, lim in LIMITES[ext]:
            if clave in ruta:
                limite = lim
        estado = "OK " if n <= limite else "EXCEDE"
        if n > limite:
            violaciones += 1
            print(f"[{estado}] {n:>4}/{limite}  {os.path.relpath(ruta, raiz)}")

print(f"\n{'✅ Todo dentro de límites' if violaciones == 0 else f'⚠️ {violaciones} archivo(s) exceden límites'}")
```

Ejecutar este script antes de cerrar cada sesión de desarrollo.
```

---

### Notas sobre cómo definí los límites (para que los valide)

1. **No son números arbitrarios de internet**: están calibrados con los tamaños REALES de tu proyecto. Por ejemplo, `pme_engine.py` (~330 líneas) es denso pero cohesivo — puse el tope de services en 400 para que quepa con margen, pero si crece más, la regla lo obliga a separar matemática de orquestación.
2. **Los 3 templates que ya exceden** (ingesta, configuración, detalle) quedan documentados como **deuda técnica aceptada del Avance 2**, no como excepciones formales — esto te obliga a ti (o a una IA futura) a hacer el refactor de partials como primera tarea de estructura, sin que el sistema se "acostumbre" a violar sus propias reglas.
3. **El script de auditoría** te da el dedito vergonzoso automático: lo corres antes de cerrar cada sesión y sabes al instante si metiste un archivo fuera de norma.

¿Estás de acuerdo con estos números, o quieres ajustar algún límite (por ejemplo, si prefieres ser más estricto con los templates: 300 en vez de 400)? También puedo generar directamente los **partials de ingesta** como primer refactor para dejar el proyecto 100% en regla desde ya.
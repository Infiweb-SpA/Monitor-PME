# 06 - Guía para Continuar el Proyecto (Cualquier LLM)

> **Instrucciones para cualquier asistente de IA que continúe EduGest PME.**
> Lee primero `00-README.md` para entender el proyecto.

---

## Reglas de oro para continuar

1. **NUNCA modifiques `app/extensions.py` ni rompas el patrón factory.**
   - Las extensiones `db` y `login_manager` DEBEN quedar en `extensions.py`
   - Si necesitas una nueva extensión, créala ahí e inicialízala en `app/__init__.py`

2. **NUNCA pongas imports circulares.**
   - Modelos importan desde `app.extensions` (NO desde `app`)
   - Rutas importan modelos desde `app.models.xxx`
   - Servicios importan modelos si es necesario, pero NO rutas

3. **Máximo 500 líneas por archivo .py.**
   - Si una ruta crece, extrae lógica a `app/services/`
   - Si un template crece, usa `{% include %}` con parciales en `templates/components/`

4. **Todo blueprint DEBE tener `template_folder="../templates/xxx"` relativo.**
   - Flask busca templates desde la carpeta del blueprint, no desde app/

5. **Si agregas una ruta POST, SIEMPRE especifica `methods=["GET", "POST"]`**
   - Flask por defecto solo acepta GET
   - Sin POST explícito, el formulario dará "Method Not Allowed"

6. **Si modificas modelos, ejecuta `python seed.py` para regenerar la DB.**
   - O usa Flask-Migrate (`flask db migrate` + `flask db upgrade`)
   - SQLite no soporta ALTER COLUMN fácilmente

7. **Mantén la coherencia visual:**
   - Sidebar: `bg-indigo-600`, íconos FontAwesome
   - Cards: `bg-white rounded-xl border border-gray-200 shadow-sm`
   - Botones primarios: `bg-indigo-600 hover:bg-indigo-700`
   - Badges de estado: cyan (En Ejecución), verde (Finalizada), gris (Planificada)

---

## Patrones de código reutilizables

### Crear una nueva ruta con formulario

```python
# app/routes/ejemplo.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.pme import AlgunaEntidad

ejemplo_bp = Blueprint("ejemplo", __name__, template_folder="../templates/ejemplo")

@ejemplo_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # Procesar formulario
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return redirect(url_for("ejemplo.index"))

        entidad = AlgunaEntidad(nombre=nombre)
        db.session.add(entidad)
        db.session.commit()
        flash("Creado correctamente.", "success")
        return redirect(url_for("ejemplo.index"))

    # GET: listar
    items = AlgunaEntidad.query.all()
    return render_template("ejemplo/index.html", items=items)
```

### Registrar nuevo blueprint

```python
# En app/__init__.py, función _registrar_blueprints(app)
from app.routes.ejemplo import ejemplo_bp
app.register_blueprint(ejemplo_bp, url_prefix="/ejemplo")
```

### Query común con filtros

```python
# Filtrar acciones por dimensión
from app.models.pme import AccionPME, DimensionPME

dim_gp = DimensionPME.query.filter_by(nombre=DimensionPME.GESTION_PEDAGOGICA).first()
acciones = AccionPME.query.filter_by(objetivo_id=dim_gp.id).all()

# Acciones con presupuesto ejecutado > 50%
acciones = AccionPME.query.filter(
    AccionPME.presupuesto_ejecutado / AccionPME.presupuesto_asignado > 0.5
).all()

# Join: estudiantes de un curso específico
from app.models.pme import Curso
from app.models.metrics import Estudiante

estudiantes = Estudiante.query.join(Curso).filter(Curso.nombre == "8° Básico").all()
```

### Usar el motor algorítmico en una ruta

```python
from app.services.pme_engine import calcular_iea, determinar_semaforo

# Después de guardar datos, recalcular indicadores
iea = calcular_iea(gasto=2500000, horas=20, delta_rendimiento=0.8, delta_asistencia=5.0)
semaforo = determinar_semaforo(proyeccion=0.92)  # → "Amarillo"
```

---

## Decisiones de diseño ya tomadas (NO cambiar)

| Decisión | Justificación |
|----------|---------------|
| SQLite en vez de PostgreSQL | Prototipado rápido, un solo colegio en Fase 1 |
| Tailwind CDN en vez de build | Simplicidad, no requiere Node.js |
| FontAwesome en vez de Lucide | Ya usado en todas las maquetas |
| Jinja2 en vez de React/Vue | Flask nativo, menos complejidad |
| Seed.py independiente | Puede ejecutarse sin levantar el servidor |
| `sys.path.insert` en seed.py | Permite ejecutar seed.py desde cualquier directorio |

---

## Dependencias instaladas (requirements.txt)

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
Werkzeug==3.0.3
pandas==2.2.2
numpy==1.26.4
python-dotenv==1.0.1
Faker==25.8.0
```

**Nota:** `scipy` NO está en requirements.txt pero se usa en `pme_engine.py` (`from scipy.stats import pearsonr`). Esto es un **bug pendiente** — agregar `scipy` a requirements.txt.

---

## Datos de prueba conocidos

Siempre que necesites probar con datos reales de la DB:

- **Admin:** `admin@liceo.cl` / `admin123`
- **Establecimiento:** RBD `78332482-2`
- **Cursos:** 5° Básico, 6° Básico, 7° Básico, 8° Básico
- **Acción hardcodeada en template:** "Taller de Refuerzo Matemático 8vo Básico" (ID ACC-123 en maqueta, ID real varía)
- **Periodos de datos:** 2026-03 a 2026-10 (Marzo a Octubre)
- **Asignaturas:** Matemáticas, Lenguaje, Ciencias, Historia, Inglés

---

## Cómo probar cambios

```bash
# 1. Recrear base de datos (si cambiaste modelos)
rm edugest_pme.db
python seed.py

# 2. Levantar servidor
python run.py

# 3. Probar en navegador
# http://localhost:5000

# 4. Para debug, activar SQL echo en app/config.py:
# SQLALCHEMY_ECHO = True  (en DevelopmentConfig)
```

---

## Contacto / Contexto previo

Este proyecto fue iniciado por **Paul Citronico** (usuario). Trabaja en el proyecto **Edugest** (Flask/Python). La última sesión previa creó reportes de notas sumativas/calificativas con promedio automático por estudiante.

**Módulos existentes en Edugest original (NO en este repo):**
- Evaluaciones y calificaciones (notas sumativas/calificativas)
- Unidades didácticas
- Reportes de notas

**Este repo es un MÓDULO NUEVO** llamado Monitor PME, enfocado en análisis cuantitativo del Plan de Mejoramiento Educativo.

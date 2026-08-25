# Monitor-PME
Prototipo de pagina y algoritmo de medición de indicadores

Para que la IA construya el proyecto respetando la estructura modular en Flask, tus archivos `.md`, las maquetas de UI y las restricciones de código, debes proporcionarle un **Master Prompt** muy estructurado.

Copia y pega la siguiente plantilla en el nuevo chat donde vas a empezar a desarrollar el código:

---

### Master Prompt para el Asistente de Código

```markdown
# PROMPT DE INICIALIZACIÓN DE PROYECTO: Monitor PME

Actúa como un Desarrollador Senior de Software en Python/Flask y Arquitecto de Software. Necesito que comencemos a construir el backend y frontend de **Monitor PME**, un módulo cuantitativo para el Plan de Mejoramiento Educativo (PME).

---

## 1. Contexto del Proyecto y Archivos de Referencia
El proyecto se basa en los archivos de especificación previamente definidos:
1. `01_flujo_sistema.md`: Flujo del usuario e ingesta de datos.
2. `02_requerimientos_proyecto.md`: Métrica del IEA, Correlación de Pearson, semáforos y requerimientos funcionales.
3. `03_limitantes_y_futuro.md`: Scope actual (carga manual/CSV) y desarrollo futuro.

Además, el diseño del frontend debe ser una copia exacta en Tailwind CSS de las maquetas visuales provistas (`loggin.jpg`, `dashboard.jpg`, `carga de datos.png`, `acciones.jpg`, `reportes.jpg`, `configuraciones.png`).

---

## 2. Estructura del Proyecto (Estricta Organización Modular)
Todo el código de la aplicación debe residir dentro del directorio raíz `app/`. No se permiten archivos fuera de esta carpeta salvo el punto de entrada `run.py`, el entorno virtual y configuraciones globales.

Estructura requerida:

```text
├── app/
│   ├── __init__.py          # Application Factory (create_app)
│   ├── config.py            # Configuración de la App y SQLite
│   ├── models/              # Modelos de SQLAlchemy
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── pme.py           # Objetivos, Acciones, Dimensiones
│   │   └── metrics.py        # Datos SIGE y App Ponderado
│   ├── routes/              # Blueprints organizados por módulo
│   │   ├── __init__.py
│   │   ├── auth.py          # /login, /logout
│   │   ├── dashboard.py     # /dashboard
│   │   ├── ingesta.py       # /ingesta (F-1, F-2, F-3, F-4)
│   │   ├── acciones.py      # /acciones, /acciones/<id>
│   │   ├── reportes.py      # /reportes
│   │   └── config.py        # /configuracion
│   ├── services/            # Lógica de Negocio y Algoritmos (Sin UI ni HTTP)
│   │   ├── __init__.py
│   │   ├── pme_engine.py    # Cálculo de IEA, Pearson y Semáforos
│   │   └── data_loader.py   # Procesamiento de cargas manuales y CSV
│   ├── templates/           # Vistas HTML con Jinja2
│   │   ├── layouts/
│   │   │   └── base.html    # Sidebar morada (#4F46E5), Header y estructura global
│   │   ├── components/      # Parciales (cards, kpis, tables, alerts)
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── ingesta/
│   │   ├── acciones/
│   │   ├── reportes/
│   │   └── configuracion/
│   └── static/              # CSS/JS personalizados si se requieren
├── seed.py                  # Script independiente para poblar la DB con datos pseudo-reales
├── run.py                   # Script de ejecución (python run.py)
└── requirements.txt

```

---

## 3. Reglas Estrictas de Desarrollo

1. **Límite de Archivos**: NINGÚN archivo `.py` puede superar las **500 líneas de código**. Separa la lógica en módulos dentro de `services/` si una ruta o modelo empieza a crecer.
2. **Población Inicial (`seed.py`)**: Toda la primera base de datos SQLite debe poblarse mediante un script independiente `seed.py`. Debe generar:
* 1 Usuario Admin / Director de prueba (`admin@liceo.cl` / `admin123`).
* 1 Establecimiento de prueba ("Liceo de Excelencia", RBD: `78332482-2`).
* 4 Cursos (5° Básico a 8° Básico(son cursos de prueba, en la implementacion final deben estar contemplados todos los cursos del establecimiento desde parvulario hasta 4to medio)).
* 10 Acciones PME en distintas dimensiones con presupuestos y estados.
* Un dataset de 200+ registros mensuales pseudo-reales con notas (1.0 a 7.0), asistencias y ejecuciones de talleres PME para calcular algoritmos reales de IEA y Correlación de Pearson.


3. **Fidelidad Estética**: El HTML generado en Jinja2 debe incluir CDN de Tailwind CSS e Íconos (Lucide Icons o FontAwesome) respetando los colores, tarjetas, tipografía y la Sidebar morada fija a la izquierda vista en las imágenes.

---

## 4. Primer Entregable Solicitado

Por favor, entrega la primera fase del proyecto construyendo lo siguiente:

1. `requirements.txt` con las dependencias necesarias (`Flask`, `Flask-SQLAlchemy`, `Pandas`, `NumPy`, `Flask-Login`).
2. `app/__init__.py` (Application Factory) y `app/config.py`.
3. Modelos SQLAlchemy dentro de `app/models/` (`user.py`, `pme.py`, `metrics.py`).
4. Script completo `seed.py` para crear las tablas y poblar los datos de prueba.

Proporciona el código de esta primera fase estructurado archivo por archivo de forma clara.





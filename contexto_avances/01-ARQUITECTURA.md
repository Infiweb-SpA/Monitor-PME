# 01 - Arquitectura del Sistema

## Patrón: Application Factory

El proyecto usa el patrón **Application Factory** de Flask. No crea la app al importar `app`, sino mediante `create_app()`.

```python
from app import create_app
app = create_app("development")
```

Esto permite:
- Tests con configuraciones diferentes
- Evitar imports circulares
- Inicializar extensiones sin app global

## Extensiones centralizadas (`app/extensions.py`)

```python
db = SQLAlchemy()
login_manager = LoginManager()
```

**IMPORTANTE:** Las extensiones viven en `extensions.py`, NO en `__init__.py`. Esto evita imports circulares entre modelos, rutas y la factory.

## Configuración por entorno (`app/config.py`)

```python
config_por_entorno = {
    "development": DevelopmentConfig,   # DEBUG=True, SQLALCHEMY_ECHO=True
    "production": ProductionConfig,   # DEBUG=False
    "testing": TestingConfig,         # SQLite en memoria, CSRF off
    "default": DevelopmentConfig,
}
```

Parámetros del algoritmo definidos en `Config`:
- `UMBRAL_SEMAFORO_ROJO = 0.85`
- `UMBRAL_SEMAFORO_AMARILLO = 0.95`
- `UMBRAL_SEMAFORO_VERDE = 1.0`

## Registro de Blueprints

Todos los blueprints se registran en `_registrar_blueprints(app)` dentro de `create_app()`:

| Blueprint | URL Prefix | Template Folder |
|-----------|-----------|-----------------|
| auth | `/auth` | `../templates/auth` |
| dashboard | `/dashboard` | `../templates/dashboard` |
| ingesta | `/ingesta` | `../templates/ingesta` |
| acciones | `/acciones` | `../templates/acciones` |
| reportes | `/reportes` | `../templates/reportes` |
| config | `/configuracion` | `../templates/configuracion` |

## Import crítico en `__init__.py`

Después de `login_manager.init_app(app)` se DEBE importar `User`:

```python
from app.models.user import User  # noqa: F401
```

Esto registra el `@login_manager.user_loader` definido en `user.py`. Sin esta línea, Flask-Login lanza `Exception: Missing user_loader`.

## Base de datos

- **Motor:** SQLite3 (`sqlite:///edugest_pme.db`)
- **ORM:** Flask-SQLAlchemy
- **Tablas creadas automáticamente** por `db.create_all()` en `create_app()`
- **Seed:** `seed.py` es independiente, usa `sys.path.insert(0, BASE_DIR)` para encontrar el paquete `app`

## Frontend

- **CSS Framework:** Tailwind CSS vía CDN (`https://cdn.tailwindcss.com`)
- **Íconos:** FontAwesome 6.4.0 vía CDN
- **Gráficos:** Placeholder para Chart.js (aún no implementado)
- **Motor de templates:** Jinja2 (incluido en Flask)
- **Layout base:** `templates/layouts/base.html` con sidebar morada fija (`#4F46E5`)

## Seguridad actual

- Contraseñas hasheadas con `werkzeug.security.generate_password_hash`
- Flask-Login maneja sesiones
- `@login_required` en todas las rutas excepto login
- CSRF: No implementado aún (Flask-WTF instalado pero no usado)

# EduGest PME - Contexto del Proyecto

> **Fecha de snapshot:** 25 de agosto de 2026
> **Estado:** Fase 1 (MVP) - Estructura base completa, login funcional, vistas estáticas maquetadas.
> **Stack:** Python 3.9+, Flask, SQLAlchemy, SQLite, Tailwind CSS, Chart.js (CDN).

---

## ¿Qué es EduGest PME?

Sistema web para la **medición cuantitativa y proyección del Plan de Mejoramiento Educativo (PME)** de establecimientos educacionales chilenos. Integra datos de:
- **App Ponderado** (notas, asistencia diaria por asignatura)
- **SIGE MINEDUC** (métricas oficiales consolidadas)
- **Acciones PME** (presupuesto, ejecución, metas)

El sistema calcula automáticamente:
- **IEA** (Índice de Eficiencia de Acción): impacto por peso invertido
- **Correlación de Pearson**: relación entre asistencia a talleres y mejora en notas
- **Semáforo predictivo**: proyección de cumplimiento de metas a fin de año

---

## Cómo ejecutar el proyecto

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear base de datos con datos de prueba
python seed.py

# 3. Levantar servidor
python run.py

# 4. Acceder
# http://localhost:5000
# Credenciales: admin@liceo.cl / admin123
```

---

## Estructura de carpetas

```
├── app/
│   ├── __init__.py          # Application Factory
│   ├── config.py            # Configuración por entorno
│   ├── extensions.py        # db, login_manager (evita imports circulares)
│   ├── models/              # SQLAlchemy ORM
│   │   ├── user.py          # Usuario + Flask-Login
│   │   ├── pme.py           # Establecimiento, Dimensiones, Objetivos, Acciones, Cursos
│   │   └── metrics.py       # Estudiantes, Registros App, SIGE, Participaciones, Indicadores
│   ├── routes/              # Blueprints Flask
│   │   ├── auth.py          # Login/Logout (FUNCIONAL)
│   │   ├── dashboard.py     # Cuadro de mando (vista estática)
│   │   ├── ingesta.py       # Formularios F-1 a F-4 (vista estática)
│   │   ├── acciones.py      # Detalle de acción PME (vista estática)
│   │   ├── reportes.py      # Generador de reportes (vista estática)
│   │   └── config.py        # Configuración del sistema (vista estática)
│   ├── services/            # Lógica de negocio (sin conexión a rutas aún)
│   │   ├── pme_engine.py    # IEA, Pearson, Semáforo, Proyección
│   │   └── data_loader.py   # Procesamiento CSV/Excel
│   ├── templates/           # Jinja2 + Tailwind CSS
│   │   ├── layouts/base.html # Sidebar morada fija, header
│   │   ├── auth/login.html  # Pantalla split login
│   │   ├── dashboard/index.html
│   │   ├── ingesta/index.html
│   │   ├── acciones/index.html
│   │   ├── reportes/index.html
│   │   └── configuracion/index.html
│   └── static/              # CSS/JS personalizados (vacío, usa CDN)
├── seed.py                  # Población de datos pseudo-reales
├── run.py                   # Punto de entrada
└── requirements.txt
```

---

## Estado resumido

| Módulo | Estado | Notas |
|--------|--------|-------|
| Login/Logout | ✅ Funcional | POST/GET, flash messages, redirect a dashboard |
| Base de datos | ✅ Funcional | SQLite, seed.py crea 60+ estudiantes, 10 acciones, 200+ registros |
| Motor algorítmico | ✅ Funcional | Funciones puras en `pme_engine.py`, usadas solo en seed |
| Dashboard | 🎨 Maqueta estática | KPIs hardcodeados, gráfico placeholder |
| Ingesta de Datos | 🎨 Maqueta estática | Formularios F-1 a F-4 visuales, sin POST |
| Acciones PME | 🎨 Maqueta estática | Vista detalle hardcodeada (Taller Matemática) |
| Reportes | 🎨 Maqueta estática | Cards de descarga + preview PDF |
| Configuración | 🎨 Maqueta estática | Tabs visuales, formulario sin POST |
| Data Loader | ⚠️ Esqueleto | Funciones vacías para CSV/Excel |

---

## Datos de prueba generados por seed.py

- **Establecimiento:** Liceo de Excelencia (RBD: 78332482-2)
- **Usuario:** admin@liceo.cl / admin123 (rol: Director)
- **Cursos:** 5° a 8° Básico
- **Estudiantes:** 60 (15 por curso)
- **Acciones PME:** 10 en 4 dimensiones
- **Registros App Ponderado:** ~2,400 (5 asignaturas × 8 meses × 60 estudiantes)
- **Métricas SIGE:** 8 mensuales
- **Indicadores calculados:** IEA, Pearson, Semáforo por acción/mes

---

## Archivos de contexto adjuntos

| Archivo | Contenido |
|---------|-----------|
| `01-ARQUITECTURA.md` | Decisiones de arquitectura, patrones, extensiones |
| `02-MODELOS_DATOS.md` | Diagrama ER, campos, relaciones, constraints |
| `03-RUTAS_Y_VISTAS.md` | Todos los blueprints, templates, URLs |
| `04-SERVICIOS_Y_ALGORITMOS.md` | Fórmulas del motor cuantitativo |
| `05-ESTADO_ACTUAL_Y_PENDIENTES.md` | TODO detallado por módulo |
| `06-GUIA_PARA_LLM.md` | Instrucciones específicas para continuar con IA |
| `ANEXO-CODIGO_COMPLETO.md` | Todo el código fuente del proyecto |

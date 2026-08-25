# 03 - Rutas (Blueprints) y Templates

## Tabla de URLs

| URL | Método | Blueprint | Función | Login Required | Estado |
|-----|--------|-----------|---------|----------------|--------|
| `/` | GET | app | index() | No | Redirect → /auth/login |
| `/auth/login` | GET, POST | auth | login() | No | ✅ Funcional |
| `/auth/logout` | GET | auth | logout() | Sí | ✅ Funcional |
| `/dashboard/` | GET | dashboard | index() | Sí | 🎨 Estático |
| `/ingesta/` | GET | ingesta | index() | Sí | 🎨 Estático |
| `/acciones/` | GET | acciones | index() | Sí | 🎨 Estático |
| `/reportes/` | GET | reportes | index() | Sí | 🎨 Estático |
| `/configuracion/` | GET | config | index() | Sí | 🎨 Estático |

**Nota:** Ninguna ruta POST (excepto login) está implementada. Los formularios en templates envían POST pero las rutas solo aceptan GET, por lo que darían "Method Not Allowed" si se intenta enviar.

---

## Descripción de cada Template

### `templates/layouts/base.html`
Layout maestro con:
- Sidebar fija a la izquierda, color indigo-600 (`#4F46E5`)
- Logo "E" en círculo blanco
- Navegación: Dashboard, Ingesta, Acciones, Reportes, Configuración
- Footer de sidebar con avatar "AD" + "Usuario Admin / Director"
- CDN: Tailwind CSS, FontAwesome 6.4.0
- Bloques Jinja2: `{% block title %}`, `{% block content %}`

### `templates/auth/login.html`
Pantalla split (50/50):
- **Izquierda:** Imagen de fondo + texto "EduGest / Sistema de Medición Cuantitativa y Proyección PME"
- **Derecha:** Formulario con campos:
  - Correo Institucional (precargado: `admin@liceo.cl`)
  - Contraseña (precargado: `admin123`)
  - Establecimiento Educativo (dropdown)
  - Año Lectivo (dropdown: 2026)
  - Botón "Iniciar Sesión"
  - Link "¿Olvidó su contraseña?"
  - Footer: "Contacte al Soporte Técnico"
- Muestra mensajes flash (success/danger/info)
- Action del form: `{{ url_for('auth.login') }}`
- Method: POST

### `templates/dashboard/index.html`
Cuadro de Mando PME 2026:
- **Header:** Título + search bar + Academic Year 2024 + iconos (bell, user)
- **4 KPI Cards:**
  1. Presupuesto PME: `$120M / $150M` (barra 80%)
  2. % Cumplimiento: `78%` (↑ +5%)
  3. IEA: `4.2 / 5.0` (barras de progreso)
  4. Alertas Activas: `12` (borde rojo izquierdo)
- **Gráfico principal:** Placeholder "Área de visualización del gráfico de dispersión"
- **Panel Alertas:** 2 alertas hardcodeadas (Taller Matemática ALTO, Tablets MEDIO)
- **Tabla seguimiento:** 1 fila de ejemplo (Capacitación Docente)

### `templates/ingesta/index.html`
Ingesta Manual de Datos:
- **Tabs:** F-1 (activo), F-2, F-3, F-4
- **Panel izquierdo — Carga Masiva:**
  - Drop zone para CSV/Excel (máx 10MB)
  - Info última carga exitosa: "12 Oct 2025 - 14:30 hrs"
  - Link "Ver historial de cargas"
- **Panel derecho — Ingesta Manual (F-1):**
  - Badge "Modo Edición"
  - Campos: Nombre Acción, Dimensión PME (dropdown), Sub-dimensión, Responsable, Estado Actual, Descripción
  - Botones: Cancelar, Sincronizar Ahora, Guardar Cambios
  - **NO tiene `action` ni `method` definidos en el form** → enviaría a la misma URL por GET

### `templates/acciones/index.html`
Detalle de Acción PME (hardcodeada: Taller de Refuerzo Matemático 8vo Básico):
- **Breadcrumb:** "← Volver a Acciones PME"
- **Header card:** Imagen + info
  - ID: ACC-123
  - Badge "En Ejecución" (cyan)
  - Presupuesto: $2.500.000
  - Responsable: Prof. Marta Díaz
  - Fechas: Mar 2024 - Nov 2024
- **Analítica de Impacto:**
  - Gráfico circular SVG con valor `0.82` (correlación de Pearson)
  - Texto: "correlación fuerte"
  - Métrica: Correlación de Pearson
- **Comparativa Rendimiento:**
  - Gráfico de barras comparativo (Grupo Beneficiado vs Grupo Control)
  - 3 periodos: Diagnóstico, Semestre 1, Semestre 2
- **Indicadores Afectados:** 4 cards (Promedio Matemáticas, % Asistencia, Participación, Satisfacción)

### `templates/reportes/index.html`
Generador de Reportes e Informes PME:
- **Header:** "Módulo de Reportes" + search bar
- **Descarga Rápida — 3 cards:**
  1. Reporte Ejecutivo Sostenedor (PDF, ícono rojo)
  2. Matriz de Rendición (Excel, ícono indigo)
  3. Informe Auditoría MINEDUC (ZIP, ícono gris)
- **Configuración de Reporte Personalizado:**
  - Periodo de Ejecución (date pickers: 01/03/2024 - 31/12/2024)
  - Dimensiones PME (checkboxes: Gestión Pedagógica ✓, Liderazgo Escolar ✓, Convivencia, Recursos)
  - Niveles/Cursos (dropdown)
  - Toggle "Incluir Medios de Verificación"
  - Preview de PDF (mockup visual)

### `templates/configuracion/index.html`
Configuración del Sistema:
- **Header:** Search bar + Academic Year 2024 + iconos (bell con punto rojo, calendar, user)
- **Tabs:** Ajustes del Colegio (activo), Parámetros del Algoritmo, Gestión de Usuarios y Roles, Integraciones
- **Información Institucional:**
  - Logo upload (placeholder EG)
  - Nombre: "Liceo Bicentenario de Excelencia"
  - RBD: "12345-6" (readonly, gris)
  - Dirección, Teléfono, Email
  - Botón "Guardar Cambios"

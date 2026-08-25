# 05 - Estado Actual y Pendientes (TODO)

## ✅ Qué FUNCIONA actualmente

### 1. Infraestructura base
- [x] Application Factory Flask
- [x] Configuración por entorno (dev/prod/test)
- [x] Extensiones centralizadas (db, login_manager)
- [x] Blueprints registrados con URL prefixes
- [x] Base de datos SQLite con SQLAlchemy ORM
- [x] Todas las tablas creadas automáticamente
- [x] Flask-Login configurado con user_loader

### 2. Autenticación
- [x] Login con email + password (hash Werkzeug)
- [x] Logout
- [x] `@login_required` en rutas protegidas
- [x] Flash messages (success/danger/info)
- [x] Redirect a login si no autenticado
- [x] Credenciales de prueba: admin@liceo.cl / admin123

### 3. Modelos de datos
- [x] 9 modelos SQLAlchemy con relaciones
- [x] User, Establecimiento, DimensionPME, ObjetivoPME, AccionPME, Curso
- [x] Estudiante, RegistroAppPonderado, MetricaSIGE, ParticipacionAccion, IndicadorAccion
- [x] Índices en campos consultados frecuentemente (email, rbd, matricula, periodo)

### 4. Seed / Datos de prueba
- [x] Script `seed.py` independiente
- [x] 1 establecimiento, 1 usuario admin, 4 cursos, 60 estudiantes
- [x] 4 dimensiones PME, 8 objetivos, 10 acciones
- [x] ~2,400 registros App Ponderado
- [x] 8 métricas SIGE mensuales
- [x] Participaciones por acción
- [x] Indicadores IEA/Pearson/Semáforo calculados automáticamente

### 5. Motor algorítmico
- [x] Función `calcular_iea()`
- [x] Función `calcular_correlacion_pearson()`
- [x] Función `determinar_semaforo()`
- [x] Función `proyectar_cumplimiento()`
- [x] Integradas en seed.py para datos de prueba

### 6. Frontend estático
- [x] Layout base con sidebar morada (#4F46E5)
- [x] Login split-screen fiel a maqueta
- [x] Dashboard con KPI cards, alertas, tabla
- [x] Ingesta con tabs F-1 a F-4, drag-drop zone
- [x] Acciones con gráfico circular SVG, barras comparativas
- [x] Reportes con cards de descarga y preview PDF
- [x] Configuración con tabs y formulario institucional

---

## ⚠️ Qué NO funciona / está incompleto

### Autenticación
- [ ] Registro de nuevos usuarios
- [ ] Recuperación de contraseña
- [ ] Gestión de roles y permisos (solo constantes definidas)
- [ ] Perfil de usuario editable
- [ ] Selección real de establecimiento/año lectivo en login

### Dashboard
- [ ] KPIs conectados a base de datos (todos hardcodeados)
- [ ] Gráfico de dispersión real (Chart.js)
- [ ] Alertas dinámicas desde base de datos
- [ ] Tabla de seguimiento con datos reales
- [ ] Filtros y paginación en tabla
- [ ] Exportar a Excel/PDF

### Ingesta de Datos (F-1 a F-4)
- [ ] POST de formulario F-1 (Registro Acciones PME)
- [ ] POST de formulario F-2 (Datos App Ponderado)
- [ ] POST de formulario F-3 (Métricas SIGE)
- [ ] POST de formulario F-4 (Asistencia Talleres)
- [ ] Carga masiva CSV/Excel funcional
- [ ] Validación de datos de entrada
- [ ] Historial de cargas
- [ ] Sincronización con base de datos

### Acciones PME
- [ ] Listado de todas las acciones (solo vista detalle hardcodeada)
- [ ] Crear nueva acción
- [ ] Editar acción existente
- [ ] Eliminar acción
- [ ] Cambiar estado (Planificada → En Ejecución → Finalizada)
- [ ] Gráficos con datos reales (IEA, Pearson, comparativas)
- [ ] Cálculo automático de indicadores al ingresar datos

### Reportes
- [ ] Generación real de PDF
- [ ] Generación real de Excel
- [ ] Generación real de ZIP
- [ ] Reporte personalizado con filtros aplicados
- [ ] Preview dinámico según selección
- [ ] Descarga con datos reales de la DB

### Configuración
- [ ] Guardar cambios de información institucional
- [ ] Upload de logo
- [ ] Tab "Parámetros del Algoritmo" (umbrales de semáforo)
- [ ] Tab "Gestión de Usuarios y Roles" (CRUD usuarios)
- [ ] Tab "Integraciones" (APIs futuras)

### Motor Algorítmico
- [ ] Ejecutar cálculos automáticamente al ingresar datos
- [ ] Cache de resultados
- [ ] Simulador "What-If" de reasignación presupuestaria
- [ ] Modelos predictivos avanzados (scikit-learn)

### Data Loader
- [ ] Procesamiento real de CSV
- [ ] Procesamiento real de Excel
- [ ] Validación de estructura de archivos
- [ ] Mapeo automático de columnas
- [ ] Reporte de errores por fila

### General
- [ ] CSRF protection (Flask-WTF instalado pero no usado)
- [ ] Manejo de errores 404, 500 personalizados
- [ ] Logs de auditoría
- [ ] Tests unitarios
- [ ] Paginación en listados
- [ ] Búsqueda funcional en todas las vistas
- [ ] Responsive mobile completo

---

## 🎯 Próximos pasos recomendados (ordenados por impacto)

### Fase 1.1 — Conectar datos a vistas (alta prioridad)
1. Hacer que Dashboard lea KPIs reales de la base de datos
2. Listar acciones PME desde DB en una tabla
3. Hacer clic en una acción y ver sus datos reales (no hardcodeado)
4. Conectar formulario F-1 para crear acciones reales

### Fase 1.2 — Ingesta funcional
5. Implementar POST de todos los formularios F-1 a F-4
6. Conectar carga masiva CSV/Excel
7. Validar datos antes de insertar

### Fase 1.3 — Motor algorítmico en vivo
8. Recalcular IEA/Pearson/Semáforo automáticamente al ingresar datos
9. Mostrar resultados en tiempo real en el dashboard
10. Generar alertas automáticas cuando proyección < 85%

### Fase 1.4 — Reportes exportables
11. Generar PDF/Excel reales con datos de la DB
12. Reporte personalizado con filtros funcionales

### Fase 2 — Escalabilidad
13. Migrar a PostgreSQL
14. APIs REST para integraciones
15. Machine Learning para predicciones

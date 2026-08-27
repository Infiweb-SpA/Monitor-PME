### Archivo 2: `contexto_avance_2/02-TAREAS_Y_MEJORAS.md`


# TAREAS PENDIENTES Y MEJORAS — EduGest PME
## Backlog por módulo (post Avance 2)

> 🔴 Crítico (bloquea comercialización) · 🟡 Importante (calidad de producto) · 🟢 Deseable (roadmap)
> Marca con [x] al completar.

---

## 🔐 MÓDULO AUTH
- [ ] 🔴 **Verificar/implementar `/auth/logout`**: el botón del sidebar apunta ahí. Si no existe
      en `routes/auth.py`, crearlo (`logout_user()` + redirect a login).
- [ ] 🔴 Validar que usuarios `activo=False` no puedan iniciar sesión (chequear en el login).
- [ ] 🟡 Restablecer contraseña (token por email o pregunta secreta para MVP sin SMTP).
- [ ] 🟡 Permisos reales por rol ( hoy los roles son solo texto: un "UTP" puede tocar
      Configuración). Decorador `@role_required('Director')` en config y usuarios.
- [ ] 🟡 Mostrar nombre/rol real del `current_user` en el sidebar (hoy dice "Usuario Admin" fijo).
- [ ] 🟢 "Seleccione establecimiento y año lectivo" al login (Paso 1.2 del flujo documentado).

## 📊 MÓDULO DASHBOARD
- [ ] 🟡 Gráfico de línea temporal: evolución mensual del promedio grupal vs línea base vs meta.
- [ ] 🟡 Los KPIs deben filtrar por año/config (`anio_activo`) — hoy suman TODO sin filtro temporal.
- [ ] 🟡 La card "IEA" y "% Cumplimiento" muestran valores parciales/estáticos: calcular el
      IEA promedio real (como en reportes `_estadisticas_globales`) y el % de acciones en verde.
- [ ] 🟡 Buscador del header: no hace nada. Conectarlo o quitarlo.
- [ ] 🟢 Campanita de notificaciones: contar alertas rojas reales.
- [ ] 🟢 Filtros por dimensión en el dashboard (drill-down del doughnut).

## 📥 MÓDULO INGESTA
- [ ] 🔴 **Validación de formato de periodo**: input text libre ("2026-08"). Usar `<input
      type="month">` o select de meses para eliminar errores de tipeo (causa #1 de "no calcula").
- [ ] 🔴 **Evitar duplicados F-4**: si el mismo alumno se carga 2 veces en la misma acción+periodo,
      las horas se suman y distorsionan Pearson. Validar antes de insertar (o upsert).
- [ ] 🟡 Carga masiva por Excel para F-2 y F-3 (hoy solo F-1 la tiene). Reutilizar el patrón
      plantilla → preview modal → guardar de acciones.
- [ ] 🟡 **Registro de gasto mensual real**: hoy `gasto_mes` del indicador = presupuesto ejecutado
      total. Formulario/campo para gasto por periodo (permitiría curva de gasto vs avance).
- [ ] 🟡 Editar/eliminar registros F-2 (un typo en una nota hoy obliga a tocar la BD).
- [ ] 🟡 Historial de cargas ("Última carga exitosa" es texto fijo): guardar log de ingesta.
- [ ] 🟢 Autocompletar alumno por matrícula en F-2.

## 🎯 MÓDULO ACCIONES
- [ ] 🔴 **Editar y eliminar acciones** (CRUD incompleto: solo crear y ver). Al eliminar, decidir
      qué pasa con participaciones/indicadores huérfanos (cascade o soft-delete).
- [ ] 🟡 **Actualizar presupuesto ejecutado** desde la UI (hoy solo se setea al crear o por BD).
- [ ] 🟡 Gráfico de tendencia histórica del indicador (ya se pasa `historico` al template pero
      no se grafica: línea de proyección_cumplimiento por mes).
- [ ] 🟡 El scatter del impacto individual: si delta es None rompe el JS (`null` en y). Sanitizar.
- [ ] 🟡 Badges de dimensión/fuente de financiamiento en el listado index.
- [ ] 🟢 Imagen de portada por acción (hoy unsplash fija de matemáticas).
- [ ] 🟢 Exportar detalle de acción a PDF individual.

## 📄 MÓDULO REPORTES
- [ ] 🟡 PDF real con librería (reportlab o weasyprint) con logo del colegio, para cuando el
      cliente no quiera "imprimir desde navegador". El HTML imprimible funciona como MVP.
- [ ] 🟡 "Incluir Medios de Verificación (Anexos)": está como "Próximamente". Modelo de adjuntos
      (boletas, certificados) vinculados a acciones — clave para trazabilidad SEP/PIE (Fase 4).
- [ ] 🟡 Filtros del personalizado: aplicar también al PDF ejecutivo y al ZIP.
- [ ] 🟡 El informe ZIP incluye datos de TODAS las acciones; respetar filtros de维度/curso.
- [ ] 🟢 Formato MINEDUC real de la "Matriz PME" (columnas del formulario oficial).
- [ ] 🟢 Envío automático por email al sostenedor (programado mensual).

## ⚙️ MÓDULO CONFIGURACIÓN
- [ ] 🔴 **Recalcular indicadores masivamente** al cambiar umbrales/pesos: hoy los cambios solo
      aplican a F-4 futuros. Botón "Recalcular todo" que re-procese IndicadorAccion de todas
      las acciones+periodos con la nueva config.
- [ ] 🟡 Validar tamaño real del logo (≤2MB, el texto lo promete pero no se valida).
- [ ] 🟡 Edición de usuarios (cambiar rol/email) y reset de contraseña por admin.
- [ ] 🟡 Usar `logo_url` en reportes ejecutivos y login (hoy solo se muestra en configuración).
- [ ] 🟢 El año activo configurado debería alimentar títulos/filtros de dashboard y reportes
      (hoy varios templates tienen "2026" escrito a mano).
- [ ] 🟢 Toggle de "Modo demo/producción" para ocultar datos seed.

## 🧠 MOTOR ALGORÍTMICO (pme_engine.py)
- [ ] 🟡 p-value real de Pearson (se retorna 0.0 fijo; reinstalar scipy o calcularlo manual).
- [ ] 🟡 Manejo de outliers: un alumno con delta extremo distorsiona r (Winsorizing o
      correlación de Spearman como alternativa robusta).
- [ ] 🟡 Pearson solo tiene sentido con notas: cuando `indicador_tipo == "Asistencia"` debería
      correlacionar horas vs delta de asistencia (hoy siempre usa notas).
- [ ] 🟡 `_nota_promedio` promedia TODAS las asignaturas: permitir filtrar por la asignatura
      objetivo de la acción (ej. taller de matemática → solo notas de matemática).
- [ ] 🟢 Proyección polinomial opcional (grado 2) cuando hay ≥6 periodos.
- [ ] 🟢 Modelo multivariable (Fase 3 roadmap: scikit-learn, Random Forest).

## 🏗️ INFRAESTRUCTURA / GENERAL
- [ ] 🔴 Protección CSRF en todos los formularios POST (Flask-WTF o token manual) — obligatorio
      antes de exponer a internet.
- [ ] 🔴 Cambiar `secret_key` de desarrollo y credenciales por variables de entorno (.env).
- [ ] 🟡 Tests unitarios del motor (pytest): casos conocidos del escenario de prueba documentado
      en 01-CONTEXTO_SISTEMA.md §6 (Pearson +1 con horas crecientes, IEA con sobregiro, etc.).
- [ ] 🟡 Paginación en listados (acciones, estudiantes del F-4) — con 300+ alumnos el
      selector y las tablas pesan.
- [ ] 🟡 Rendimiento: `procesar_indicadores_accion` hace N queries por alumno (N+1). Con 500
      alumnos optimizar con queries agregadas (RNF-02: ≤2 segundos).
- [ ] 🟢 Multi-tenant real: TODO hardcodea `Establecimiento.query.first()` y
      `establecimiento_id=1` en ingesta SIGE. Debe venir del usuario logueado.
- [ ] 🟢 Despliegue: Dockerfile + gunicorn, o guía de instalación para colegios (instalador).
- [ ] 🟢 Auditoría de accesos (log de quién cargó qué dato y cuándo) — valor comercial para
      la Superintendencia.

## 🗂️ DATOS / SEED
- [ ] 🟡 El seed genera indicadores con `proyeccion_simulada` aleatoria (no usa el motor real
      sobre los datos): hacer que seed llame a `procesar_indicadores_accion` por acción/periodo
      para que el demo tenga consistencia matemática real.
- [ ] 🟡 Seed: crear también fila de ConfiguracionSistema explícita.
- [ ] 🟢 Script de seed con perfiles configurables (colegio grande 500 alumnos / pequeño 60).

---

## Prioridad sugerida para próxima sesión de trabajo
1. Auth logout + validación usuario activo (🔴, 30 min)
2. Input type="month" en periodos + validación duplicados F-4 (🔴)
3. CRUD editar/eliminar acciones + actualizar presupuesto ejecutado desde UI (🔴/🟡)
4. Botón "Recalcular indicadores" en Configuración (🔴 para demo coherente)
5. Gráfico de tendencia histórica en detalle (🟡, ya hay datos)
```

---

### Recomendación de uso

1. **Crea la carpeta** `contexto_avance_2/` en la raíz y guarda ambos archivos ahí.
2. Cuando abras una nueva conversación conmigo (u otra IA), pega el contenido de `01-CONTEXTO_SISTEMA.md` y pide lo que necesites: *"Aquí está el contexto del sistema, quiero trabajar en [X] del backlog"*.
3. Cada vez que completes una tarea del backlog, márcala con `[x]` — así los documentos nunca quedan desactualizados.

El archivo de contexto incluye deliberadamente la sección de **bugs resueltos** y la **decisión de diseño** del PDF imprimible, porque son el tipo de conocimiento que se pierde entre conversaciones y hace que una IA te vuelva a proponer lo mismo que ya descartamos.

¿Quieres que ajuste algo de la lista de tareas (agregar/quitar prioridades) o seguimos directamente con el primer ítem del backlog sugerido (verificar el `/auth/logout`)?
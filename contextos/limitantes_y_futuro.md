# Limitantes y Hoja de Ruta Futura (Roadmap)
## Sistema de Análisis Cuantitativo y Proyección PME - EduGest

Este documento establece las restricciones operativas actuales del proyecto debido a la falta de credenciales/interconexiones directas, así como las oportunidades de desarrollo e innovación para versiones futuras del software.

---

## 1. Limitantes Actuales del Sistema (Fase 1 / MVP)

1. **Ausencia de Integración Directa por API**:
   * *Descripción*: Debido a que no se dispone de credenciales directas de acceso ni al SIGE (Mineduc) ni al sistema comercial actual (App Ponderado), la ingesta depende de cargas manuales o archivos de importación CSV/Excel.
   * *Impacto*: Existe un riesgo de sesgo por error humano en la digitación o un retraso en la actualización del cuadro de mando si el equipo no carga los datos oportunamente.

2. **Cálculo Basado en Modelos Simplificados**:
   * *Descripción*: Para la versión inicial con SQLite y Python, se implementarán modelos de regresión lineal simple y correlación de Pearson.
   * *Impacto*: No se consideran variables exógenas complejas (ej. nivel socioeconómico, paros de profesores, factores climáticos) que puedan influir en el rendimiento o la asistencia de un mes específico.

3. **Volumen de Datos Históricos Variable**:
   * *Descripción*: La precisión de las proyecciones cuantitativas depende directamente de la cantidad de períodos históricos registrados.
   * *Impacto*: En establecimientos con menos de un semestre de datos digitados, el semáforo predictivo mostrará un margen de incertidumbre más amplio.

4. **Persistencia en SQLite**:
   * *Descripción*: SQLite es ideal para demostraciones y prototipos locales, pero presenta limitaciones de concurrencia para múltiples colegios o múltiples usuarios escribiendo simultáneamente en producción masiva.

---

## 2. Hoja de Ruta y Desarrollo a Futuro (Roadmap)

### Fase 2: Automatización y Web Scraping / APIs Directas
* **Conectores Automáticos**: Desarrollar scripts de integración directa o *web scrapers* autorizados que extraigan la información consolidada desde el SIGE y App Ponderado automáticamente sin intervención humana.
* **Migración de Base de Datos**: Escalabilidad desde SQLite hacia **PostgreSQL** para dar soporte multitenant (múltiples colegios simultáneos) con roles granularizados.

### Fase 3: Algoritmos Avanzados y Machine Learning
* **Modelo Predictivo de Regresión Múltiple / Random Forest**: Incorporar librerías como `scikit-learn` en Python para predecir no solo si la meta del PME se cumplirá, sino qué factor específico (ej. asistencia, tipo de taller, docente a cargo) tiene mayor peso en el éxito.
* **Simulador de Escenarios "What-If" (Reasignación Presupuestaria)**:
  * Permitir al Sostenedor simular redistribuciones de presupuesto en tiempo real: *"Si muevo $2.000.000 de la Acción A (que muestra baja eficiencia) a la Acción B, ¿cuánto aumenta la probabilidad de cumplir la meta del PME?"*.

### Fase 4: Módulo de Reportabilidad Oficial y Auditoría MINEDUC
* **Generación Automática de Documentos PME**: Creación de informes ejecutivos en PDF diseñados con estándares institucionales listos para presentar ante la Agencia de Calidad de la Educación y la Superintendencia de Educación.
* **Trazabilidad de Gastos SEP/PIE**: Módulo de auditoría que garantice la rendición clara de cuentas asociando cada boleta/factura con el impacto pedagógico medido por el algoritmo.
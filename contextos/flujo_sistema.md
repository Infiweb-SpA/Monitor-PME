# Flujo de Trabajo del Sistema (Workflow)
## Módulo de Medición y Proyección Cuantitativa del PME - EduGest

Este documento describe el flujo conceptual y de usuario paso a paso dentro del sistema EduGest, enfocado en el análisis de impacto del Plan de Mejoramiento Educativo (PME) mediante la integración de datos simulados/manuales del SIGE y App Ponderado.

---

## 1. Autenticación y Control de Acceso
* **Paso 1.1: Inicio de Sesión**
  * El usuario (Director, UTP, Encargado PME o Sostenedor) ingresa a la plataforma mediante su correo institucional y contraseña.
* **Paso 1.2: Selección del Establecimiento y Año Lectivo**
  * El usuario selecciona el colegio activo y el año de gestión del PME a evaluar (ej. Año 2026).

---

## 2. Configuración e Ingesta de Datos (Carga de Información)
Debido a la ausencia de APIs directas en primera fase, la carga se realiza mediante **Ingreso Manual Estructurado** o **Importación en Lote (CSV/Excel)**.

* **Paso 2.1: Definición del Marco PME (Formulario 1)**
  * El Encargado de PME registra las **Dimensiones**, **Objetivos**, **Acciones**, **Presupuesto Asignado** y **Metas Cuyo Impacto se Desea Medir**.
* **Paso 2.2: Ingesta de Datos Internos / App Ponderado (Formulario 2)**
  * Carga o digitación periódica (mensual/bimensual) de:
    * Asistencia por estudiante/curso.
    * Calificaciones / Evaluaciones parciales por asignatura.
    * Bitácora de ejecución física de la acción (% de avance, asistencia de alumnos al taller/reforzamiento).
* **Paso 2.3: Ingesta de Datos Oficiales / SIGE (Formulario 3)**
  * Carga de métricas oficiales consolidadas del SIGE:
    * Matrícula oficial y retiro de estudiantes.
    * Asistencia acumulada validada.
    * Promedios de rendimiento trimestral/semestral.

---

## 3. Procesamiento y Motor Algorítmico (Backend Flask + SQLite)
Una vez guardados los datos, el motor cuantitativo de EduGest ejecuta de forma autónoma:
1. **Consolidación de Datos**: Cruce de la participación del alumno en la Acción PME vs. sus notas y asistencia registradas en App Ponderado / SIGE.
2. **Cálculo del Índice de Eficiencia de Acción (IEA)**: Evalúa cuánto impacto positivo generó cada peso invertido o cada hora de taller ejecutada.
3. **Análisis de Correlación de Pearson**: Identifica si existe relación directa entre asistir a una acción PME y la mejora en las notas/asistencia.
4. **Algoritmo de Semáforo / Proyección de Cumplimiento**: Simula el rendimiento futuro a fin de año e identifica desvíos respecto a la meta PME.

---

## 4. Visualización y Toma de Decisiones (Dashboard)
* **Paso 4.1: Vista General / Cuadro de Mando Ejecutivo**
  * Resumen global: % de Presupuesto Ejecutado vs. % de Logro Estimado del PME.
  * Alertas tempranas de acciones con bajo impacto o desvío crítico (Semáforos Rojo/Amarillo).
* **Paso 4.2: Análisis por Acción / Dimensión PME**
  * Gráficos comparativos de líneas y barras (Generados dinámicamente) que muestran el comportamiento del grupo intervenido vs. el grupo de control/curso completo.
* **Paso 4.3: Exportación de Informes de Gestión**
  * Generación de reportes ejecutivos en PDF/Excel para reuniones de equipo directivo o presentación al Sostenedor.

---

## 5. Diagrama Simplificado del Flujo

```
[Inicio de Sesión]
       │
       ▼
[Módulo PME: Registro de Objetivos y Acciones]
       │
       ├───────────────► [Formulario Carga SIGE] ──┐
       │                                          │
       └───────────────► [Formulario Carga App Ponderado] ──┤
                                                  │
                                                  ▼
                                     [Motor Algorítmico EduGest]
                                     (IEA + Correlación + Proyección)
                                                  │
                                                  ▼
                                     [Dashboard y Alertas Tempranas]
                                                  │
                                                  ▼
                                     [Exportación de Informes PME]
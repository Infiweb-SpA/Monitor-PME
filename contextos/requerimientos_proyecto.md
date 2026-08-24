# Requerimientos del Proyecto
## Sistema de Análisis Cuantitativo y Proyección PME - EduGest

Este documento especifica los requerimientos funcionales, no funcionales, el inventario de formularios requeridos y el listado de datos pseudo-reales/reales necesarios para la validación del prototipo.

---

## 1. Arquitectura Tecnológica Definida
* **Lenguaje Backend**: Python 3.x
* **Framework Web**: Flask
* **Base de Datos**: SQLite3 (ligero, ideal para prototipado rápido y pruebas locales)
* **Frontend / Estilos**: HTML5 + Tailwind CSS + JavaScript Vanilla (o Alpine.js para interactividad liviana)
* **Visualización de Datos**: Chart.js (integrado mediante CDN/JS)
* **Procesamiento de Datos**: Pandas / NumPy (para cálculos estadísticos y análisis de correlación en Python)

---

## 2. Requerimientos Funcionales (RF)

### RF-01: Gestión del Plan de Mejoramiento Educativo (PME)
* **RF-01.1**: Permitir la creación, edición y eliminación de Objetivos y Metas Anuales del PME clasificadas por las 4 dimensiones oficiales (Gestión Pedagógica, Liderazgo, Convivencia Escolar, Gestión de Recursos).
* **RF-01.2**: Asignación de Presupuesto (SEP/PIE/Subvención) y responsables a cada Acción del PME.

### RF-02: Módulo de Ingesta Manual y Carga Pseudo-Real
* **RF-02.1**: Interfaz web intuitiva para digitar o importar masivamente datos provenientes de la gestión diaria (App Ponderado) y reportes oficiales (SIGE).
* **RF-02.2**: Script generador de datos pseudo-reales (*Seed Data*) para realizar simulaciones cuantitativas con 300+ alumnos y 2 años de trayectoria.

### RF-03: Motor Algorítmico de Cálculo Cuantitativo
* **RF-03.1 (Índice de Eficiencia de Acción - IEA)**: Algoritmo que calcula la relación entre el presupuesto gastado/horas ejecutadas y la variación positiva en el rendimiento/asistencia.
* **RF-03.2 (Análisis de Correlación de Pearson)**: Cálculo automático del coeficiente de correlación ($r$) entre la participación en una Acción PME y la mejora individual/grupal en notas o asistencia.
* **RF-03.3 (Algoritmo de Alerta Temprana y Semáforo)**: Proyección lineal o polinomial simple del indicador a fin de año.
  * **Rojo**: Proyección < 85% de cumplimiento de la meta.
  * **Amarillo**: Proyección entre 85% y 95% de cumplimiento.
  * **Verde**: Proyección $\ge$ 95% de cumplimiento.

### RF-04: Dashboard e Informes
* **RF-04.1**: Visualización de gráficos de rendimiento (comparación de línea base vs. valor actual vs. meta).
* **RF-04.2**: Listado interactivo de alertas de desviaciones presupuestarias y pedagógicas.

---

## 3. Requerimientos No Funcionales (RNF)
* **RNF-01 (Facilidad de Uso)**: La interfaz debe requerir menos de 3 clics para acceder a las alertas del PME.
* **RNF-02 (Rendimiento)**: El cálculo de los indicadores para un colegio con 500 alumnos y 20 acciones no debe superar los 2 segundos de ejecución en SQLite.
* **RNF-03 (Modularidad)**: El código en Flask debe estar estructurado en *Blueprints* para facilitar la futura integración directa por API cuando las credenciales estén disponibles.

---

## 4. Listado de Formularios a Crear

Para capturar la información necesaria sin requerir integraciones automáticas iniciales, se construirán 4 formularios clave:

| # | Nombre del Formulario | Propósito / Campos Principales |
|---|-----------------------|--------------------------------|
| **F-1** | **Registro de Acciones PME** | Dimensión, Nombre de la Acción, Meta Cualitativa, Meta Cuantitativa (ej. "+5% Asistencia"), Presupuesto Asignado ($), Curso/Grupo Objetivo. |
| **F-2** | **Carga de Datos App Ponderado** | Periodo (Mes/Trimestre), Curso, Asignatura, Promedio de Notas, % Asistencia Mensual, Bitácora de ejecución física de la acción PME. |
| **F-3** | **Carga de Métricas Oficiales SIGE** | Año, Mes, Matrícula Oficial, % Asistencia Oficial Validada, Calificaciones Consolidadas por Curso. |
| **F-4** | **Seguimiento de Participantes por Acción** | Matrícula de Alumnos, Acción PME vinculada, Horas de Asistencia/Asistencia a Talleres de Reforzamiento. |

---

## 5. Listado de Datos Reales Necesarios para Testeo Final

Para validar el sistema con el establecimiento educativo una vez aprobada la prueba de concepto, se solicitarán las siguientes planillas/reportes en formato Excel o CSV:

1. **Estructura del PME Actual**:
   * Matriz PME aprobada (Objetivos, Acciones, Presupuestos asignados por acción).
2. **Histórico SIGE (Últimos 1 a 2 años)**:
   * Reporte de asistencia mensual consolidada por curso.
   * Planilla de rendimiento anual/semestral por asignatura y estudiante.
3. **Reportes Exportados de App Ponderado**:
   * Registro de notas parciales y del libro de clases digital.
   * Registro de asistencias diarias por asignatura.
   * Bitácoras o registros de intervenciones de pie/reforzamiento (si existen).
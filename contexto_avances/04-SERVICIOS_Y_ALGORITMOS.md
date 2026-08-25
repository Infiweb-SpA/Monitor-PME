# 04 - Servicios y Algoritmos

## `app/services/pme_engine.py`

Módulo de funciones puras (sin dependencias de Flask ni DB). Calcula métricas cuantitativas del PME.

### `calcular_iea(gasto_ejecutado, horas_ejecutadas, delta_rendimiento, delta_asistencia)`

**Índice de Eficiencia de Acción (IEA)**

Fórmula conceptual: `impacto / recurso`

```
impacto = (delta_rendimiento * 0.6) + (delta_asistencia * 0.4)
recurso = (gasto_ejecutado / 1_000_000) + (horas_ejecutadas / 10)
iea = min(5.0, max(0.0, (impacto / recurso) * 10))
```

- Retorna valor entre `0.0` y `5.0`
- Si `gasto_ejecutado <= 0` o `horas_ejecutadas <= 0`, retorna `0.0`
- Pesos: 60% rendimiento académico, 40% asistencia

**Uso actual:** Solo en `seed.py` para generar datos de prueba.

---

### `calcular_correlacion_pearson(x, y)`

Calcula el coeficiente de correlación de Pearson entre dos arrays.

```python
from scipy.stats import pearsonr
r, p = pearsonr(x, y)
return round(r, 3), round(p, 4)
```

- `x`: Array de valores (ej. horas de asistencia a taller)
- `y`: Array de valores (ej. mejora en notas)
- Retorna `(None, None)` si arrays tienen < 2 elementos o longitudes distintas
- Retorna `(coeficiente_r, valor_p)`

**Interpretación de r:**
- `|r| > 0.7` → Correlación fuerte
- `0.3 < |r| < 0.7` → Correlación moderada
- `|r| < 0.3` → Correlación débil

**Uso actual:** En `seed.py` para calcular correlación entre horas de participación y delta de notas por acción.

---

### `determinar_semaforo(proyeccion_cumplimiento, umbral_rojo=0.85, umbral_amarillo=0.95)`

Retorna el estado del semáforo según proyección:

| Proyección | Retorno | Color |
|-----------|---------|-------|
| `< 0.85` | `"Rojo"` | 🔴 |
| `0.85 - 0.94` | `"Amarillo"` | 🟡 |
| `>= 0.95` | `"Verde"` | 🟢 |

**Umbrales configurables** vía `app.config`: `UMBRAL_SEMAFORO_ROJO`, `UMBRAL_SEMAFORO_AMARILLO`.

---

### `proyectar_cumplimiento(valores_historicos, meta)`

Proyección lineal simple a fin de año usando `numpy.polyfit`.

```python
x = np.arange(n)          # índices 0, 1, 2...
y = np.array(valores_historicos)
m, b = np.polyfit(x, y, 1)  # y = mx + b
proyeccion = m * 11 + b       # proyectar al mes 12 (índice 11)
cumplimiento = proyeccion / meta
```

- Si `< 2` valores históricos, usa el último valor directo
- Retorna valor entre `0.0` y `2.0` (capado)

**Uso actual:** En `seed.py` para generar proyecciones mensuales.

---

## `app/services/data_loader.py`

Esqueleto para procesamiento de archivos. **No conectado a rutas aún.**

### `procesar_csv_acciones(file_stream)`
- Lee CSV con pandas
- Retorna `list[dict]` o `{"error": str}`

### `procesar_excel_metricas(file_stream)`
- Lee Excel (.xlsx) con pandas
- Retorna `list[dict]` o `{"error": str}`

**Pendiente:**
- Validación de columnas requeridas
- Mapeo de columnas a modelos SQLAlchemy
- Inserción batch a base de datos
- Manejo de duplicados

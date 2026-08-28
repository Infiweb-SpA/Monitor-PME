"""Pruebas unitarias del motor algorítmico PME.

Cubre:
- calcular_progreso_indicador() con todas las direcciones y casos especiales
- calcular_correlacion_pearson() con muestras pequeñas
- Pesos y normalización
"""
import sys
import os

# Agregar la raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pme_engine import (
    calcular_progreso_indicador,
    calcular_correlacion_pearson,
    calcular_iea,
)


# ============================================================
# PROGRESO: MAYOR_ES_MEJOR
# ============================================================

def test_mayor_es_mejor_caso_normal():
    """base=60, actual=95, meta=120 → progreso ≈ 58.33%"""
    r = calcular_progreso_indicador(60, 95, 120, "MAYOR_ES_MEJOR")
    assert r["delta"] == 35.0
    assert abs(r["progreso_meta"] - 58.33) < 0.1
    assert r["estado"] == "EN_PROGRESO"


def test_mayor_es_mejor_meta_alcanzada():
    """base=60, actual=130, meta=120 → progreso > 100%"""
    r = calcular_progreso_indicador(60, 130, 120, "MAYOR_ES_MEJOR")
    assert r["delta"] == 70.0
    assert r["progreso_meta"] > 100
    assert r["estado"] == "META_ALCANZADA"


def test_mayor_es_mejor_retroceso():
    """base=60, actual=50, meta=120 → progreso < 0"""
    r = calcular_progreso_indicador(60, 50, 120, "MAYOR_ES_MEJOR")
    assert r["delta"] == -10.0
    assert r["progreso_meta"] < 0
    assert r["estado"] == "RETROCESO"


def test_mayor_es_mejor_sin_cambio():
    """base=60, actual=60, meta=120 → progreso = 0%"""
    r = calcular_progreso_indicador(60, 60, 120, "MAYOR_ES_MEJOR")
    assert r["delta"] == 0.0
    assert r["progreso_meta"] == 0.0
    assert r["estado"] == "ESTABLE"


# ============================================================
# PROGRESO: MENOR_ES_MEJOR
# ============================================================

def test_menor_es_mejor_caso_normal():
    """base=15, actual=8, meta=5 → progreso = 70%"""
    r = calcular_progreso_indicador(15, 8, 5, "MENOR_ES_MEJOR")
    assert r["delta"] == -7.0
    assert abs(r["progreso_meta"] - 70.0) < 0.1
    assert r["estado"] == "EN_PROGRESO"


def test_menor_es_mejor_meta_alcanzada():
    """base=15, actual=3, meta=5 → progreso > 100%"""
    r = calcular_progreso_indicador(15, 3, 5, "MENOR_ES_MEJOR")
    assert r["delta"] == -12.0
    assert r["progreso_meta"] > 100
    assert r["estado"] == "META_ALCANZADA"


def test_menor_es_mejor_retroceso():
    """base=15, actual=20, meta=5 → progreso < 0"""
    r = calcular_progreso_indicador(15, 20, 5, "MENOR_ES_MEJOR")
    assert r["delta"] == 5.0
    assert r["progreso_meta"] < 0
    assert r["estado"] == "RETROCESO"


# ============================================================
# CASOS ESPECIALES
# ============================================================

def test_base_igual_meta():
    """base=120, actual=120, meta=120 → SIN_BRECHA"""
    r = calcular_progreso_indicador(120, 120, 120, "MAYOR_ES_MEJOR")
    assert r["estado"] == "SIN_BRECHA"
    assert r["delta"] == 0.0


def test_base_sobre_meta_mayor():
    """base=130, actual=135, meta=120 → META_ALCANZADA (ya cumplía)"""
    r = calcular_progreso_indicador(130, 135, 120, "MAYOR_ES_MEJOR")
    assert r["estado"] == "META_ALCANZADA"
    assert r["delta"] == 5.0


def test_base_sobre_meta_menor():
    """base=3, actual=2, meta=5 → META_ALCANZADA (ya cumplía en MENOR_ES_MEJOR)"""
    r = calcular_progreso_indicador(3, 2, 5, "MENOR_ES_MEJOR")
    assert r["estado"] == "META_ALCANZADA"


def test_valores_none():
    """Cualquier None → SIN_DATOS"""
    r = calcular_progreso_indicador(None, 95, 120, "MAYOR_ES_MEJOR")
    assert r["estado"] == "SIN_DATOS"
    r2 = calcular_progreso_indicador(60, None, 120, "MAYOR_ES_MEJOR")
    assert r2["estado"] == "SIN_DATOS"
    r3 = calcular_progreso_indicador(60, 95, None, "MAYOR_ES_MEJOR")
    assert r3["estado"] == "SIN_DATOS"


# ============================================================
# PEARSON
# ============================================================

def test_pearson_muestra_insuficiente():
    """n < 2 → None"""
    r, _ = calcular_correlacion_pearson([10], [50])
    assert r is None


def test_pearson_dos_puntos():
    """n = 2 → r = +1 o -1 (dos puntos = línea perfecta)"""
    r, _ = calcular_correlacion_pearson([5, 45], [10, 90])
    assert r is not None
    assert abs(r) == 1.0 or abs(r - 1.0) < 0.01


def test_pearson_positivo():
    """Correlación positiva clara"""
    r, _ = calcular_correlacion_pearson([5, 10, 20, 30, 40], [10, 20, 42, 60, 75])
    assert r is not None
    assert r > 0.7


def test_pearson_arrays_vacios():
    """Arrays vacíos → None"""
    r, _ = calcular_correlacion_pearson([], [])
    assert r is None


# ============================================================
# IEA
# ============================================================

def test_iea_basico():
    """IEA con parámetros normales"""
    iea = calcular_iea(500000, 50, 0.5, 5.0, 500000)
    assert 0 <= iea <= 5.0


def test_iea_sobregiro():
    """IEA con gasto > presupuesto → penalización"""
    iea_normal = calcular_iea(500000, 50, 0.5, 5.0, 500000)
    iea_sobregiro = calcular_iea(850000, 50, 0.5, 5.0, 500000)
    assert iea_sobregiro < iea_normal


def test_iea_gasto_cero():
    """Gasto 0 → IEA 0"""
    iea = calcular_iea(0, 50, 0.5, 5.0, 500000)
    assert iea == 0.0


# ============================================================
# PESOS
# ============================================================

def test_pesos_suman_100():
    """Verificar que 30+50+20=100 funciona como pesos de IPA"""
    pesos = [30, 50, 20]
    progresos = [58.3, 80.0, 70.0]
    total_peso = sum(pesos)
    ipa = sum(p * w for p, w in zip(progresos, pesos)) / total_peso
    assert abs(ipa - 71.49) < 0.1


def test_pesos_normalizacion():
    """Pesos que no suman 100 deben normalizarse"""
    pesos = [3, 5, 2]  # suman 10, equivalente a 30/50/20
    progresos = [58.3, 80.0, 70.0]
    total_peso = sum(pesos)
    ipa = sum(p * w for p, w in zip(progresos, pesos)) / total_peso
    assert abs(ipa - 71.49) < 0.1


# ============================================================
# ESCENARIO COMPLETO (sección 39 de la especificación)
# ============================================================

def test_escenario_completo_velocidad_lectora():
    """Escenario: Taller de comprensión lectora, velocidad lectora MAYOR_ES_MEJOR"""
    # Alumno A: base 60, actual 95, meta 120
    a = calcular_progreso_indicador(60, 95, 120, "MAYOR_ES_MEJOR")
    assert abs(a["progreso_meta"] - 58.33) < 0.1
    assert a["delta"] == 35.0

    # Alumno B: base 80, actual 110, meta 120
    b = calcular_progreso_indicador(80, 110, 120, "MAYOR_ES_MEJOR")
    assert abs(b["progreso_meta"] - 75.0) < 0.1
    assert b["delta"] == 30.0

    # Alumno C: base 100, actual 115, meta 120
    c = calcular_progreso_indicador(100, 115, 120, "MAYOR_ES_MEJOR")
    assert abs(c["progreso_meta"] - 75.0) < 0.1
    assert c["delta"] == 15.0

    # Pearson: horas vs progreso
    horas = [20, 30, 35]
    progresos = [a["progreso_meta"], b["progreso_meta"], c["progreso_meta"]]
    r, _ = calcular_correlacion_pearson(horas, progresos)
    assert r is not None
    # Debe ser positivo (más horas → más progreso)
    assert r > 0


def test_escenario_multiple_indicadores():
    """Escenario: 3 indicadores con pesos 30/50/20"""
    vel = calcular_progreso_indicador(60, 95, 120, "MAYOR_ES_MEJOR")
    prec = calcular_progreso_indicador(75, 91, 95, "MAYOR_ES_MEJOR")
    err = calcular_progreso_indicador(20, 8, 5, "MENOR_ES_MEJOR")

    pesos = [30, 50, 20]
    progresos = [vel["progreso_meta"], prec["progreso_meta"], err["progreso_meta"]]
    total_peso = sum(pesos)
    ipa = sum(p * w for p, w in zip(progresos, pesos)) / total_peso

    # IPA debe estar entre 0 y 100
    assert 0 < ipa < 100
    # Verificar que los progresos individuales son correctos
    assert abs(vel["progreso_meta"] - 58.33) < 0.1
    # prec: (91-75)/(95-75) = 16/20 = 80%
    assert abs(prec["progreso_meta"] - 80.0) < 0.1
    # err: (20-8)/(20-5) = 12/15 = 80%
    assert abs(err["progreso_meta"] - 80.0) < 0.1


# ============================================================
# EJECUTAR TODAS LAS PRUEBAS
# ============================================================

if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Resultado: {passed} pasadas, {failed} falladas de {len(tests)} totales")
    if failed == 0:
        print("✅ TODAS LAS PRUEBAS PASARON")
    else:
        print("⚠️ HAY PRUEBAS FALLIDAS — revisar arriba")
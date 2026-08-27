#!/usr/bin/env python3
"""Audita el cumplimiento de las reglas de líneas por archivo."""
import os

LIMITES = {
    ".py": [("routes", 300), ("services", 400), ("models", 250), ("__init__.py", 120)],
    ".html": [("partials", 150), ("macros", 200), ("ejecutivo", 300)],
}
DEFAULT_PY, DEFAULT_HTML = 350, 400  # defaults: scripts raíz / templates normales

raiz = os.path.dirname(os.path.abspath(__file__))
violaciones = 0

for carpeta, _, archivos in os.walk(raiz):
    if any(x in carpeta for x in ["__pycache__", ".git", "instance", "node_modules"]):
        continue
    for arch in archivos:
        ext = os.path.splitext(arch)[1]
        if ext not in (".py", ".html"):
            continue
        ruta = os.path.join(carpeta, arch)
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            n = sum(1 for _ in f)
        limite = DEFAULT_PY if ext == ".py" else DEFAULT_HTML
        for clave, lim in LIMITES[ext]:
            if clave in ruta:
                limite = lim
        estado = "OK " if n <= limite else "EXCEDE"
        if n > limite:
            violaciones += 1
            print(f"[{estado}] {n:>4}/{limite}  {os.path.relpath(ruta, raiz)}")

print(f"\n{'✅ Todo dentro de límites' if violaciones == 0 else f'⚠️ {violaciones} archivo(s) exceden límites'}")
"""Compara la exportación secuencial (un proceso tras otro) con la paralela (todos a la vez).

Uso:
    python3 psp/comparar.py                      # con la base real de RedKyber
    python3 psp/comparar.py --filas 200000       # con una base temporal sintética (8 tablas de 200000 filas)
    python3 psp/comparar.py --filas 200000 --repeticiones 7

Los datos sintéticos se crean en una carpeta temporal: la base real no se toca.
"""
import argparse
import os
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import closing

DIR_PSP = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_PSP)
TRABAJADOR = os.path.join(DIR_PSP, "exportar_tabla.py")


def listar_tablas(ruta_db):
    with closing(sqlite3.connect(f"file:{ruta_db}?mode=ro", uri=True)) as conn:
        filas = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [f[0] for f in filas]


def crear_base_sintetica(ruta, tablas, filas):
    """8 tablas con la misma forma, para que la comparación sea justa."""
    with closing(sqlite3.connect(ruta)) as conn:
        for i in range(tablas):
            conn.execute(f'CREATE TABLE datos{i} (id INTEGER PRIMARY KEY, nombre TEXT, valor REAL, nota TEXT)')
            conn.executemany(
                f'INSERT INTO datos{i} (nombre, valor, nota) VALUES (?, ?, ?)',
                ((f"registro {n}", n * 1.5, "x" * 20) for n in range(filas)),
            )
        conn.commit()
    return [f"datos{i}" for i in range(tablas)]


def secuencial(tablas, entorno):
    inicio = time.perf_counter()
    for tabla in tablas:
        r = subprocess.run([sys.executable, TRABAJADOR, tabla], env=entorno, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
    return (time.perf_counter() - inicio) * 1000


def paralelo(tablas, entorno):
    inicio = time.perf_counter()
    procesos = [
        subprocess.Popen([sys.executable, TRABAJADOR, t], env=entorno, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for t in tablas
    ]
    for p in procesos:
        _, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(err)
    return (time.perf_counter() - inicio) * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filas", type=int, default=0, help="filas por tabla en una base sintética (0 = base real)")
    ap.add_argument("--repeticiones", type=int, default=5)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        entorno = dict(os.environ, REDKYBER_SALIDA=os.path.join(tmp, "salida"))
        if args.filas > 0:
            ruta_db = os.path.join(tmp, "prueba.db")
            tablas = crear_base_sintetica(ruta_db, 8, args.filas)
            origen = f"base sintética: {len(tablas)} tablas x {args.filas} filas"
        else:
            ruta_db = os.path.join(DIR_PROYECTO, "data", "redkyber.db")
            tablas = listar_tablas(ruta_db)
            origen = f"base real de RedKyber: {len(tablas)} tablas"
        entorno["REDKYBER_DB"] = ruta_db

        print(f"Origen: {origen}")
        print(f"Núcleos de la CPU: {os.cpu_count()} | repeticiones: {args.repeticiones}\n")

        seq, par = [], []
        # Se alternan para que el calentamiento del disco y la caché afecten a los dos por igual
        for _ in range(args.repeticiones):
            seq.append(secuencial(tablas, entorno))
            par.append(paralelo(tablas, entorno))

        ms, mp = statistics.median(seq), statistics.median(par)
        print(f"{'Modo':<12} | {'Mediana (ms)':>13} | {'Mín (ms)':>9} | {'Máx (ms)':>9}")
        print("-" * 52)
        print(f"{'Secuencial':<12} | {ms:>13.1f} | {min(seq):>9.1f} | {max(seq):>9.1f}")
        print(f"{'Paralelo':<12} | {mp:>13.1f} | {min(par):>9.1f} | {max(par):>9.1f}")
        print(f"\nAceleración (secuencial / paralelo): {ms / mp:.2f}x")


if __name__ == "__main__":
    main()

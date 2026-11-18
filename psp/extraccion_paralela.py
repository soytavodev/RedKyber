import sys
import os
import sqlite3
import subprocess
import time
from contextlib import closing
from datetime import datetime

def main():
    # Construir rutas relativas al directorio del proyecto (un nivel arriba de psp/)
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    dir_proyecto = os.path.dirname(dir_actual)

    ruta_db = os.environ.get("REDKYBER_DB", os.path.join(dir_proyecto, "data", "redkyber.db"))
    dir_salida = os.environ.get("REDKYBER_SALIDA", os.path.join(dir_proyecto, "data", "extracciones_psp"))
    ruta_trabajador = os.path.join(dir_actual, "exportar_tabla.py")

    try:
        # 1. Leer nombres de las tablas de sqlite_master en modo solo lectura
        uri_db = f"file:{ruta_db}?mode=ro"
        with closing(sqlite3.connect(uri_db, uri=True)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tablas = [fila[0] for fila in cursor.fetchall()]

        if not tablas:
            print("No se encontraron tablas en la base de datos.")
            sys.exit(0)

        # Con --fallo se añade una tabla que no existe, para probar el manejo de errores
        if "--fallo" in sys.argv:
            tablas.append("tabla_que_no_existe")

        inicio = time.perf_counter()

        # 2. Lanzar todos los subprocesos en paralelo (sin esperar dentro del bucle)
        procesos = []
        for tabla in tablas:
            proc = subprocess.Popen(
                [sys.executable, ruta_trabajador, tabla],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            procesos.append((tabla, proc))

        # 3. Esperar a que terminen, recoger su salida e imprimir el resumen
        print(f"{'TABLA':<25} | {'PID':<8} | {'EXIT':<5} | {'SALIDA'}")
        print("-" * 75)

        errores = 0
        lineas_registro = []
        for tabla, proc in procesos:
            stdout, stderr = proc.communicate()
            codigo = proc.returncode

            if codigo == 0:
                mensaje = stdout.strip()
            else:
                errores += 1
                mensaje = f"ERROR: {stderr.strip()}"

            print(f"{tabla:<25} | {proc.pid:<8} | {codigo:<5} | {mensaje}")
            lineas_registro.append(f"{tabla} | pid {proc.pid} | salida {codigo} | {mensaje}")

        total_ms = (time.perf_counter() - inicio) * 1000
        print(f"\nTiempo total (paralelo): {total_ms:.1f} ms")

        # Registro: una cabecera por ejecución y una línea por tabla
        os.makedirs(dir_salida, exist_ok=True)
        with open(os.path.join(dir_salida, "registro.log"), "a", encoding="utf-8") as reg:
            reg.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {len(tablas)} tablas | {errores} errores | {total_ms:.1f} ms\n")
            for linea in lineas_registro:
                reg.write("    " + linea.replace("\n", " ") + "\n")

        # Salir con código 1 si algún trabajador falló
        sys.exit(1 if errores > 0 else 0)

    except Exception as e:
        print(f"Error en el coordinador: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
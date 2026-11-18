import sys
import os
import sqlite3
import csv
from contextlib import closing

def main():
    if len(sys.argv) < 2:
        print("Error: falta el nombre de la tabla como argumento.", file=sys.stderr)
        sys.exit(1)

    tabla = sys.argv[1]

    # Construir rutas relativas al directorio del proyecto (un nivel arriba de psp/)
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    dir_proyecto = os.path.dirname(dir_actual)

    # Las variables de entorno permiten medir con otra base sin tocar la real
    ruta_db = os.environ.get("REDKYBER_DB", os.path.join(dir_proyecto, "data", "redkyber.db"))
    dir_salida = os.environ.get("REDKYBER_SALIDA", os.path.join(dir_proyecto, "data", "extracciones_psp"))
    ruta_csv = os.path.join(dir_salida, f"{tabla}.csv")

    try:
        # 2. Abrir base de datos en modo solo lectura usando URI
        uri_db = f"file:{ruta_db}?mode=ro"
        # closing cierra la conexión de verdad (el "with" solo confirma la transacción)
        with closing(sqlite3.connect(uri_db, uri=True)) as conn:
            cursor = conn.cursor()

            # Validación básica para evitar caracteres inválidos en el nombre de tabla
            if not tabla.isidentifier():
                raise ValueError(f"Nombre de tabla no válido: '{tabla}'")

            # 3. Consultar todos los registros y escribir el CSV (nombre entre comillas)
            cursor.execute(f'SELECT * FROM "{tabla}"')
            filas = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]

            os.makedirs(dir_salida, exist_ok=True)

            with open(ruta_csv, mode="w", newline="", encoding="utf-8") as archivo_csv:
                escritor = csv.writer(archivo_csv)
                escritor.writerow(columnas)  # Cabeceras
                escritor.writerows(filas)    # Datos

        # 4. Resultado exitoso
        print(f"{tabla}: {len(filas)} filas")
        sys.exit(0)

    except Exception as e:
        print(f"Error exportando '{tabla}': {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
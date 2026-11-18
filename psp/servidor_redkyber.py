import socket
import threading
import sqlite3
import os
import logging
from contextlib import closing

IP = "127.0.0.1"
PUERTO = 5050

# Lista fija de tablas permitidas
TABLAS_VALIDAS = {
    "clientes",
    "productos",
    "empleados",
    "proveedores",
    "pedidos",
    "lineaspedido",
    "componentes",
    "consultas",
}

# Ruta de la base de datos (variable de entorno o relativa a __file__)
DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_ACTUAL)
RUTA_DB = os.environ.get(
    "REDKYBER_DB",
    os.path.join(DIR_PROYECTO, "data", "redkyber.db")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(DIR_ACTUAL, "registro_servidor.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def conectar_db():
    uri_db = f"file:{RUTA_DB}?mode=ro"
    return sqlite3.connect(uri_db, uri=True)


def formatear(filas):
    lineas = ["|".join(str(c) if c is not None else "" for c in fila) for fila in filas]
    lineas.append("FIN")
    return "\n".join(lineas) + "\n"


def procesar_comando(linea):
    partes = linea.strip().split(maxsplit=2)
    if not partes:
        return "ERROR comando no válido\nFIN\n"

    accion = partes[0].upper()

    if accion == "LISTAR":
        if len(partes) != 2:
            return "ERROR comando no válido\nFIN\n"

        tabla = partes[1].lower()
        if tabla not in TABLAS_VALIDAS:
            return f"ERROR tabla '{tabla}' no permitida\nFIN\n"

        try:
            with closing(conectar_db()) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {tabla}")
                filas = cursor.fetchall()

            return formatear(filas)

        except Exception as e:
            logging.error("Error interno: %s", e)
            return f"ERROR interno: {e}\nFIN\n"

    elif accion == "BUSCAR":
        if len(partes) < 3:
            return "ERROR comando no válido\nFIN\n"

        tabla = partes[1].lower()
        texto = partes[2]

        if tabla not in TABLAS_VALIDAS:
            return f"ERROR tabla '{tabla}' no permitida\nFIN\n"

        try:
            with closing(conectar_db()) as conn:
                cursor = conn.cursor()
                # Obtener nombres de columnas de la tabla validada
                cursor.execute(f"PRAGMA table_info({tabla})")
                columnas = [col[1] for col in cursor.fetchall()]

                # Construir cláusula WHERE segura con parámetros (?)
                condiciones = [f"CAST({col} AS TEXT) LIKE ?" for col in columnas]
                where_sql = " OR ".join(condiciones)
                patron = f"%{texto}%"
                parametros = [patron] * len(columnas)

                cursor.execute(f"SELECT * FROM {tabla} WHERE {where_sql}", parametros)
                filas = cursor.fetchall()

            return formatear(filas)

        except Exception as e:
            logging.error("Error interno: %s", e)
            return f"ERROR interno: {e}\nFIN\n"

    else:
        return "ERROR comando no válido\nFIN\n"


def atender_cliente(conexion, direccion):
    logging.info("Cliente conectado desde %s", direccion)
    buffer = b""

    with closing(conexion):
        try:
            while True:
                datos = conexion.recv(1024)
                if not datos:
                    # El cliente cerró la conexión
                    break

                buffer += datos

                if len(buffer) > 4096:
                    logging.warning("Cliente %s superó el límite de línea", direccion)
                    conexion.sendall("ERROR línea demasiado larga\nFIN\n".encode("utf-8"))
                    return

                # Procesar comando por cada línea recibida
                while b"\n" in buffer:
                    linea, buffer = buffer.split(b"\n", 1)
                    linea = linea.decode("utf-8", errors="replace").strip()

                    if not linea:
                        continue

                    if linea.upper() == "SALIR":
                        conexion.sendall("Adiós\nFIN\n".encode("utf-8"))
                        return

                    respuesta = procesar_comando(linea)
                    conexion.sendall(respuesta.encode("utf-8"))

        except ConnectionResetError:
            pass
        except Exception as e:
            logging.error("Error con cliente %s: %s", direccion, e)
        finally:
            logging.info("Cliente desconectado %s", direccion)


def iniciar_servidor():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((IP, PUERTO))
        servidor.listen()

        logging.info("Servidor escuchando en %s:%s", IP, PUERTO)
        logging.info("Base de datos: %s", RUTA_DB)

        try:
            while True:
                conexion, direccion = servidor.accept()
                hilo = threading.Thread(
                    target=atender_cliente,
                    args=(conexion, direccion),
                    name=f"cliente-{direccion[1]}",
                    daemon=True
                )
                hilo.start()
        except KeyboardInterrupt:
            logging.info("Deteniendo el servidor...")


if __name__ == "__main__":
    iniciar_servidor()
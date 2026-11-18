import socket
import sys
from contextlib import closing

IP = "127.0.0.1"
PUERTO = 5050


def recibir_respuesta(archivo):
    lineas = []
    while True:
        linea = archivo.readline()
        if linea == "":
            raise ConnectionError("El servidor cerró la conexión")

        linea_limpia = linea.rstrip("\r\n")
        if linea_limpia == "FIN":
            break

        lineas.append(linea_limpia)

    return lineas


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else IP
    try:
        puerto = int(sys.argv[2]) if len(sys.argv) > 2 else PUERTO
    except ValueError:
        print("Error: el puerto debe ser un número entero.", file=sys.stderr)
        sys.exit(1)

    try:
        conexion = socket.create_connection((ip, puerto), timeout=5)
    except ConnectionRefusedError:
        print("No se pudo conectar: ¿está arrancado el servidor?", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error de conexión: {e}", file=sys.stderr)
        sys.exit(1)

    with closing(conexion):
        conexion.settimeout(None)
        archivo = conexion.makefile("rw", encoding="utf-8", newline="\n")

        with closing(archivo):
            print(f"Conectado a {ip}:{puerto}")
            print("Comandos disponibles: LISTAR <tabla> | BUSCAR <tabla> <texto> | SALIR")

            try:
                while True:
                    try:
                        comando = input("> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        archivo.write("SALIR\n")
                        archivo.flush()
                        break

                    if not comando:
                        continue

                    archivo.write(comando + "\n")
                    archivo.flush()

                    respuesta = recibir_respuesta(archivo)
                    for linea in respuesta:
                        print(linea)

                    if comando.upper() == "SALIR":
                        break

            except (ConnectionError, OSError) as e:
                print(f"Error de comunicación: {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
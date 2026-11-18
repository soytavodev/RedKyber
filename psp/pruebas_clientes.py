import socket
import sys
import threading
import time
from contextlib import closing

IP = "127.0.0.1"
PUERTO = 5050
CONSULTAS = [
    "LISTAR clientes",
    "LISTAR productos",
    "BUSCAR clientes España",
    "LISTAR usuarios",
]


def recibir_respuesta(archivo):
    lineas = []
    while True:
        linea = archivo.readline()
        if linea == "":
            raise ConnectionError("El servidor cerró la conexión inesperadamente")

        linea_limpia = linea.rstrip("\r\n")
        if linea_limpia == "FIN":
            break

        lineas.append(linea_limpia)

    return lineas


def cliente_de_prueba(numero, repeticiones, resultados):
    total_esperado = repeticiones * len(CONSULTAS)
    correctas = 0
    incorrectas = 0

    try:
        conexion = socket.create_connection((IP, PUERTO), timeout=5)
        with closing(conexion):
            conexion.settimeout(None)
            archivo = conexion.makefile("rw", encoding="utf-8", newline="\n")

            with closing(archivo):
                for _ in range(repeticiones):
                    for consulta in CONSULTAS:
                        archivo.write(consulta + "\n")
                        archivo.flush()

                        respuesta = recibir_respuesta(archivo)

                        if consulta.startswith("LISTAR usuarios"):
                            # Debe devolver exactamente 1 línea que empiece por ERROR
                            if len(respuesta) == 1 and respuesta[0].startswith("ERROR"):
                                correctas += 1
                            else:
                                incorrectas += 1
                        else:
                            # Debe devolver al menos 1 línea y ninguna puede empezar por ERROR
                            if len(respuesta) >= 1 and not any(
                                linea.startswith("ERROR") for linea in respuesta
                            ):
                                correctas += 1
                            else:
                                incorrectas += 1

                        # Simula la pausa de un cliente real entre peticiones
                        time.sleep(0.05)

                # Cierre limpio de sesión
                archivo.write("SALIR\n")
                archivo.flush()
                recibir_respuesta(archivo)

        resultados[numero] = (correctas, incorrectas)

    except (OSError, ConnectionError):
        resultados[numero] = (0, total_esperado)


def ejecutar_paralelo(n_clientes, repeticiones):
    resultados = [None] * n_clientes
    hilos = []

    for i in range(n_clientes):
        hilo = threading.Thread(
            target=cliente_de_prueba,
            args=(i, repeticiones, resultados),
            name=f"test-worker-{i}",
        )
        hilos.append(hilo)

    inicio = time.perf_counter()

    # 1. Arrancar todos los hilos primero para que compitan simultáneamente
    for hilo in hilos:
        hilo.start()

    # 2. Esperar a que todos terminen
    for hilo in hilos:
        hilo.join()

    duracion = time.perf_counter() - inicio
    return resultados, duracion


def ejecutar_secuencial(n_clientes, repeticiones):
    resultados = [None] * n_clientes

    inicio = time.perf_counter()
    for i in range(n_clientes):
        cliente_de_prueba(i, repeticiones, resultados)
    duracion = time.perf_counter() - inicio

    return resultados, duracion


def resumir_resultados(nombre_modo, resultados, duracion):
    total_correctas = sum(r[0] for r in resultados)
    total_incorrectas = sum(r[1] for r in resultados)
    total_consultas = total_correctas + total_incorrectas

    print(f"--- Modo {nombre_modo} ---")
    print(f"Consultas totales : {total_consultas}")
    print(f"Correctas         : {total_correctas}")
    print(f"Incorrectas       : {total_incorrectas}")
    print(f"Tiempo total      : {duracion:.4f} s\n")


def main():
    try:
        n_clientes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        repeticiones = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        if n_clientes <= 0 or repeticiones <= 0:
            raise ValueError
    except ValueError:
        print(
            "Error: el número de clientes y las repeticiones deben ser enteros positivos.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Iniciando prueba de carga: {n_clientes} clientes x {repeticiones} repeticiones...\n")

    res_par, tiempo_par = ejecutar_paralelo(n_clientes, repeticiones)
    resumir_resultados("PARALELO (Hilos)", res_par, tiempo_par)

    res_sec, tiempo_sec = ejecutar_secuencial(n_clientes, repeticiones)
    resumir_resultados("SECUENCIAL (Sin hilos)", res_sec, tiempo_sec)

    if tiempo_par > 0:
        proporcion = tiempo_sec / tiempo_par
        print(f"Proporción: El modo paralelo fue {proporcion:.2f}x más rápido que el secuencial.")


if __name__ == "__main__":
    main()
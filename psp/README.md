# PSP · Procesos y comunicaciones en red

Parte de PSP (Programación de servicios y procesos) aplicada a RedKyber. Toma la base `data/redkyber.db` y exporta cada tabla a CSV **con un proceso distinto por tabla**, en lugar de hacerlo una tras otra como en `servicios/extraccion.php`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `exportar_tabla.py` | Proceso trabajador. Recibe el nombre de una tabla, la lee en modo solo lectura y escribe su CSV. Devuelve código 0 si fue bien y 1 si falló |
| `extraccion_paralela.py` | Proceso coordinador. Lee las tablas, lanza un `subprocess.Popen` por tabla sin esperar, y después recoge la salida y el código de cada uno. Escribe `registro.log` y muestra el PID de cada proceso |
| `comparar.py` | Mide el tiempo de hacerlo en secuencial y en paralelo y calcula la aceleración |

## Cómo ejecutarlo

```bash
cd RedKyber
python3 psp/extraccion_paralela.py            # exporta las tablas en paralelo
python3 psp/extraccion_paralela.py --fallo    # añade una tabla que no existe para probar el manejo de errores
python3 psp/comparar.py                       # compara con la base real
python3 psp/comparar.py --filas 200000        # compara con una base temporal de 8 tablas de 200 000 filas
```

Los CSV y el registro quedan en `data/extracciones_psp/` (no se suben a git). No hace falta instalar nada: solo Python 3 con la librería estándar.

## Cómo funciona

1. El coordinador lanza todos los trabajadores en un primer bucle, sin esperar a ninguno, así que corren a la vez.
2. En un segundo bucle espera a cada uno con `communicate()`, que devuelve lo que imprimió, y mira su `returncode`.
3. Si algún trabajador falla, lo anota en el registro y el coordinador termina con código 1, pero los demás siguen exportándose.

La información se comparte con el trabajador por **argumentos** (la tabla) y **variables de entorno** (`REDKYBER_DB` y `REDKYBER_SALIDA`, solo para las pruebas), y vuelve por la **salida estándar**, el **código de salida** y los **archivos CSV**.

## Mediciones

Hechas en mi portátil (16 hilos), con la mediana de varias repeticiones alternando los dos modos:

| Datos | Secuencial | Paralelo | Aceleración |
|---|---|---|---|
| Base real (8 tablas, de 2 a 16 filas) | 126,9 ms | 19,9 ms | 6,38x |
| Sintética: 8 tablas de 200 000 filas | 2280 ms | 381 ms | 5,98x |
| Sintética: 8 tablas de 1 000 000 filas | 10 954 ms | 1903 ms | 5,76x |

Los datos sintéticos se crean en una carpeta temporal y solo sirven para esta prueba; la base real no se modifica. La mejora no llega a 8x porque el disco y el arranque de cada proceso se comparten.

## Uso de la IA

Escribí a mano la primera versión de `exportar_tabla.py` y de `extraccion_paralela.py`, siguiendo una guía de pasos que me dio la IA (qué debía hacer cada archivo y por qué hacen falta dos bucles). La IA revisó los dos archivos y luego agregó el registro en `registro.log`, la opción `--fallo`, el cierre de la conexión, las comillas en el nombre de la tabla, las variables de entorno y el programa `comparar.py`. La idea de lanzar un proceso por tabla, la elección de Python y de las tablas de RedKyber la decidí yo. Las mediciones las ejecuté en mi computadora y no están inventadas.

---

# Servicio de consultas por sockets (RA3)

En esta parte hice un servidor TCP que consulta `data/redkyber.db` y atiende a varios clientes a la vez, con un hilo por cliente. En el RA1 usé procesos distintos; aquí uso hilos dentro de un mismo proceso, porque los clientes solo comparten el servidor y no necesitan memoria separada. La base se abre siempre en modo solo lectura.

## Archivos

| Archivo | Qué hace |
|---|---|
| `servidor_redkyber.py` | Acepta conexiones y crea un hilo por cliente. Responde a los comandos y escribe `registro_servidor.log` con la hora y el nombre del hilo |
| `cliente_redkyber.py` | Cliente de consola. Se conecta, envía lo que escribo y muestra la respuesta hasta la línea `FIN` |
| `pruebas_clientes.py` | Lanza varios clientes a la vez, comprueba cada respuesta y compara con hacerlo uno detrás de otro |

## Protocolo

| Comando | Respuesta |
|---|---|
| `LISTAR <tabla>` | Todas las filas de la tabla |
| `BUSCAR <tabla> <texto>` | Las filas donde alguna columna contiene el texto |
| `SALIR` | Un adiós y se cierra la conexión |

- Cada comando termina con un salto de línea.
- Cada respuesta tiene una fila por línea, con los campos separados por `|`, y termina con una línea `FIN`.
- Los errores empiezan por `ERROR` y también terminan con `FIN`, así el cliente siempre sabe cuándo acabó la respuesta.

## Cómo ejecutarlo

Primero se arranca el servidor en una terminal y se deja abierto:

```bash
cd RedKyber
python3 psp/servidor_redkyber.py
```

Después, en otra terminal, se abre el cliente o las pruebas:

```bash
cd RedKyber
python3 psp/cliente_redkyber.py
python3 psp/pruebas_clientes.py 10 5     # 10 clientes, 5 repeticiones cada uno
```

El servidor se detiene con `Ctrl+C`. El cliente acepta la IP y el puerto como argumentos (`python3 psp/cliente_redkyber.py 127.0.0.1 5050`). No hace falta instalar nada: solo Python 3 con la librería estándar.

## Decisiones

- **TCP y no UDP.** Las consultas necesitan que la respuesta llegue completa y en orden.
- **Un hilo por cliente.** Es lo que vimos en clase y evita que un cliente lento bloquee a los demás.
- **Sin `Lock`.** Cada hilo abre su propia conexión a SQLite y no comparten ningún dato, así que no hay nada que proteger. En el ejemplo de clase sí hace falta porque los hilos comparten la lista de clientes.
- **Seguridad.** Solo se aceptan las 8 tablas de una lista fija, el texto de `BUSCAR` va como parámetro `?` y no dentro del SQL, y la base está en solo lectura. Probé con `' OR 1=1 --` y no devolvió filas.
- **Límite de línea.** Si un cliente envía más de 4096 bytes sin salto de línea, el servidor le responde con un error y cierra la conexión, para que no llene la memoria.
- **Bytes y no texto.** El servidor acumula bytes y decodifica solo la línea completa, porque una tilde puede llegar partida entre dos envíos.
- **Solo local.** Escucha en `127.0.0.1`, así que solo acepta conexiones de la misma computadora.

## Mediciones

Hechas en mi portátil (16 hilos), con el servidor local. Cada cliente hace cuatro consultas por repetición (tres válidas y una con error a propósito) y espera 0,05 s entre una y otra, como haría una persona. Todas las respuestas fueron correctas.

| Clientes × repeticiones | Consultas | Con hilos (varios clientes a la vez) | Sin hilos (uno detrás de otro) | Aceleración |
|---|---|---|---|---|
| 10 × 5 | 200 | 1,02 s | 10,11 s | 9,91x |
| 50 × 5 | 1000 | 1,03 s | 50,56 s | 48,95x |

El tiempo con hilos casi no cambia entre 10 y 50 clientes, que es lo que demuestra que el servidor los atiende a la vez. La aceleración sale sobre todo de la pausa de 0,05 s: lo que mide es la simultaneidad, no que el servidor sea más rápido en sí. En el registro se ve cómo los nombres de hilo (`cliente-XXXXX`) se solapan.

## Uso de la IA

Escribí a mano `servidor_redkyber.py`, `cliente_redkyber.py` y `pruebas_clientes.py`, siguiendo una guía de pasos que me dio la IA. La IA revisó los tres archivos y me propuso tres mejoras para el servidor (acumular bytes, limitar la línea y usar `logging`), que apliqué yo. También agregó `psp/*.log` al `.gitignore` y redactó esta sección del README. Las pruebas y las mediciones las ejecuté yo en mi computadora, y la IA las repitió para comprobarlas con resultados casi iguales. La idea del servicio, los comandos y la elección de Python y de las tablas de RedKyber las decidí yo.

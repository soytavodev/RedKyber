# PSP · Exportación de tablas en paralelo

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

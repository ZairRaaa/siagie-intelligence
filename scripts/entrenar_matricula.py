"""Selecciona modelos con validación temporal y ejecuta la prueba histórica reservada."""

import argparse
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from threadpoolctl import threadpool_limits

from src.ml.artefactos import (
    CLAVES_PARES, MANIFIESTO, MODELOS, PROTOCOLO, directorio_ejecucion, leer_json,
    leer_particion, ruta_particion, sha256_archivo,
)
from src.ml.evaluacion import metricas, metricas_segmentadas, tamanos
from src.ml.modelos import SEMILLA, candidatos, construir_modelo
from src.ml.panel import OBJETIVO


def escribir_json(ruta, datos):
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False) + "\n", "utf-8")
    temporal.replace(ruta)


def parametros_protocolo(manifiesto, hilos):
    return {
        "version_protocolo": PROTOCOLO,
        "sha256_panel": manifiesto["sha256_panel_canonico"],
        "particiones_sha256": {
            nombre: manifiesto["artefactos"][nombre]["sha256"]
            for nombre in ("entrenamiento", "validacion", "prueba")
        },
        "semilla": SEMILLA, "hilos": hilos, "seleccion": "MAE mínimo en validación",
        "recorte_predicciones": "máximo entre la estimación y cero",
        "versiones": {
            "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__,
        },
        "candidatos": [
            {"id": c.id, "modelo": c.modelo, "variables": list(c.variables), "parametros": c.parametros}
            for c in candidatos()
        ],
    }


def ajustar(candidato, datos):
    modelo = construir_modelo(candidato)
    if modelo is not None:
        modelo.fit(datos[list(candidato.variables)], datos[OBJETIVO])
    return modelo


def predecir(candidato, modelo, datos):
    if modelo is None:
        return datos.matricula_t.to_numpy(dtype="float64")
    return np.maximum(0, modelo.predict(datos[list(candidato.variables)]))


def elegir_validacion(resultados):
    # min conserva el primero en empates exactos según el orden preestablecido.
    finalistas = {
        modelo: min((fila for fila in resultados if fila["modelo"] == modelo), key=lambda fila: fila["mae"])
        for modelo in MODELOS
    }
    elegido = min(finalistas.values(), key=lambda fila: fila["mae"])
    return {modelo: fila["id"] for modelo, fila in finalistas.items()}, elegido["modelo"]


def seleccionar(protocolo, entrenamiento, validacion):
    resultados = []
    for candidato in candidatos():
        inicio = perf_counter()
        print(f"Validación · {candidato.id}", flush=True)
        modelo = ajustar(candidato, entrenamiento)
        predicho = predecir(candidato, modelo, validacion)
        resultados.append({
            "id": candidato.id, "modelo": candidato.modelo,
            **metricas(validacion[OBJETIVO], predicho), "segundos": round(perf_counter() - inicio, 3),
        })
    finalistas, elegido = elegir_validacion(resultados)
    return {"protocolo": protocolo, "validacion": resultados, "finalistas": finalistas, "elegido": elegido}


def evaluar_final(carpeta, manifiesto, seleccion, entrenamiento, validacion, inicio):
    disponibles = {candidato.id: candidato for candidato in candidatos()}
    finalistas = {modelo: disponibles[clave] for modelo, clave in seleccion["finalistas"].items()}
    desarrollo = pd.concat([entrenamiento, validacion], ignore_index=True)
    ajustados = {}
    for clave, candidato in finalistas.items():
        print(f"Reajuste con entrenamiento y validación · {clave}", flush=True)
        ajustados[clave] = ajustar(candidato, desarrollo)

    print("Evaluando la prueba histórica reservada · 2023 a 2024", flush=True)
    prueba = leer_particion(manifiesto, "prueba")
    base = prueba[[*CLAVES_PARES, "nivel_t", "gestion_t", "matricula_t", OBJETIVO]]
    base = base.rename(columns={OBJETIVO: "real"}).assign(tamano=tamanos(prueba.matricula_t))
    evaluaciones, tablas = [], []
    for clave, candidato in finalistas.items():
        predicho = predecir(candidato, ajustados[clave], prueba)
        evaluaciones.append({"modelo": clave, **metricas(base.real, predicho)})
        tablas.append(base.assign(modelo=clave, predicho=predicho, error=predicho - base.real))
    metricas_prueba = pd.DataFrame(evaluaciones)
    predicciones = pd.concat(tablas, ignore_index=True)
    segmentos = pd.DataFrame(metricas_segmentadas(predicciones))

    with TemporaryDirectory(dir=carpeta) as temporal:
        salida = Path(temporal)
        predicciones.to_parquet(salida / "predicciones.parquet", index=False)
        pd.DataFrame(seleccion["validacion"]).to_csv(salida / "metricas_validacion.csv", index=False)
        metricas_prueba.to_csv(salida / "metricas_prueba.csv", index=False)
        segmentos.to_csv(salida / "metricas_segmentos.csv", index=False)
        for clave, modelo in ajustados.items():
            if modelo is not None:
                joblib.dump(modelo, salida / f"{clave}.joblib")
        artefactos = {ruta.name: sha256_archivo(ruta) for ruta in sorted(salida.iterdir())}
        for ruta in salida.iterdir():
            ruta.replace(carpeta / ruta.name)
    escribir_json(carpeta / "resumen.json", {
        "fecha": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "origen": manifiesto["fuente"], "particiones": manifiesto["particiones"],
        "sha256_panel": manifiesto["sha256_panel_canonico"],
        "elegido": seleccion["elegido"], "finalistas": seleccion["finalistas"],
        "metricas_prueba": evaluaciones, "artefactos_sha256": artefactos,
        "segundos_ejecucion": round(perf_counter() - inicio, 3),
    })
    print(metricas_prueba.to_string(index=False), flush=True)
    print(f"Resultados guardados en {carpeta}", flush=True)


def ejecutar(manifiesto, hilos):
    inicio = perf_counter()
    carpeta = directorio_ejecucion(manifiesto)
    carpeta.mkdir(parents=True, exist_ok=True)
    candado = carpeta / ".entrenamiento.lock"
    try:
        with candado.open("x", encoding="ascii") as archivo:
            archivo.write(str(os.getpid()))
    except FileExistsError as error:
        raise ValueError(f"Hay una ejecución en curso o interrumpida. Revisa {candado}.") from error
    try:
        if (carpeta / "resumen.json").is_file():
            print(f"La prueba histórica de este protocolo ya está registrada en {carpeta}.")
            return
        protocolo = parametros_protocolo(manifiesto, hilos)
        entrenamiento = leer_particion(manifiesto, "entrenamiento")
        validacion = leer_particion(manifiesto, "validacion")
        with threadpool_limits(limits=hilos):
            ruta_seleccion = carpeta / "seleccion.json"
            if ruta_seleccion.is_file():
                seleccion = leer_json(ruta_seleccion)
                if seleccion["protocolo"] != protocolo:
                    raise ValueError("La ejecución debe reanudarse con las versiones y los hilos de la selección guardada.")
            else:
                seleccion = seleccionar(protocolo, entrenamiento, validacion)
                escribir_json(ruta_seleccion, seleccion)
            evaluar_final(carpeta, manifiesto, seleccion, entrenamiento, validacion, inicio)
    finally:
        candado.unlink(missing_ok=True)


def verificar(manifiesto, hilos):
    protocolo = parametros_protocolo(manifiesto, hilos)
    for nombre in ("entrenamiento", "validacion"):
        print(f"{nombre}: {len(leer_particion(manifiesto, nombre))} pares verificados")
    ruta_particion(manifiesto, "prueba")
    for candidato in candidatos():
        construir_modelo(candidato)
    print(f"Prueba reservada: huella verificada. scikit-learn {protocolo['versiones']['scikit_learn']}.")
    print("Entorno y configuraciones listos. Modelos ajustados: 0.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Comprueba el entorno sin ajustar modelos.")
    parser.add_argument("--hilos", type=int, default=2, help="Límite de hilos internos, por defecto 2.")
    args = parser.parse_args()
    if args.hilos < 1:
        parser.error("--hilos debe ser al menos 1.")
    try:
        manifiesto = leer_json(MANIFIESTO)
        accion = verificar if args.verificar else ejecutar
        accion(manifiesto, args.hilos)
    except (OSError, ValueError, KeyError) as error:
        print(f"ML: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nEjecución interrumpida. Puedes reanudar con el mismo comando.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

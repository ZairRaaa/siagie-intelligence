"""Audita la ejecución publicada y puede exportar una figura de la prueba histórica."""

import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.ml.artefactos import (
    CLAVES_PARES, MANIFIESTO, METRICAS, MODELOS, ROOT, directorio_ejecucion, leer_json,
    leer_particion, sha256_archivo,
)
from src.ml.panel import OBJETIVO


def _calcular(real, predicho):
    distancia = predicho.to_numpy() - real.to_numpy()
    dispersion = float(((real - real.mean()) ** 2).sum())
    return {
        "n": len(real), "mae": np.abs(distancia).mean(), "rmse": np.sqrt((distancia ** 2).mean()),
        "r2": 1 - (distancia ** 2).sum() / dispersion if dispersion else None,
        "wape": np.abs(distancia).sum() * 100 / real.sum() if real.sum() else None,
    }


def _comparar_tablas(primera, segunda, claves):
    pd.testing.assert_frame_equal(
        primera.sort_values(claves, ignore_index=True),
        segunda.sort_values(claves, ignore_index=True),
        check_dtype=False, rtol=1e-12, atol=1e-12,
    )


def auditar():
    manifiesto = leer_json(MANIFIESTO)
    carpeta = directorio_ejecucion(manifiesto)
    resumen = leer_json(carpeta / "resumen.json")
    seleccion = leer_json(carpeta / "seleccion.json")
    protocolo = seleccion["protocolo"]
    huella_panel = manifiesto["sha256_panel_canonico"]
    if (
        resumen["sha256_panel"] != huella_panel or protocolo["sha256_panel"] != huella_panel
        or resumen["particiones"] != manifiesto["particiones"]
        or any(
            protocolo["particiones_sha256"][nombre] != manifiesto["artefactos"][nombre]["sha256"]
            for nombre in ("entrenamiento", "validacion", "prueba")
        )
    ):
        raise ValueError("La ejecución corresponde a otra versión del panel o de las particiones.")

    nombres = {"predicciones.parquet", "metricas_segmentos.csv", "metricas_prueba.csv",
               "metricas_validacion.csv", "ridge.joblib", "hgb.joblib"}
    huellas = resumen["artefactos_sha256"]
    if nombres != huellas.keys() or any(sha256_archivo(carpeta / n) != huellas[n] for n in nombres):
        raise ValueError("Los archivos de la ejecución y sus huellas difieren.")

    validacion = pd.read_csv(carpeta / "metricas_validacion.csv")
    _comparar_tablas(validacion, pd.DataFrame(seleccion["validacion"]), ["id"])
    if validacion.id.tolist() != [candidato["id"] for candidato in protocolo["candidatos"]]:
        raise ValueError("Los candidatos evaluados difieren del protocolo.")
    finalistas = validacion.loc[validacion.groupby("modelo").mae.idxmin()].set_index("modelo")
    elegido = min(MODELOS, key=lambda modelo: finalistas.loc[modelo, "mae"])
    if (finalistas.id.to_dict() != seleccion["finalistas"] or elegido != seleccion["elegido"]
            or resumen["elegido"] != elegido or resumen["finalistas"] != seleccion["finalistas"]):
        raise ValueError("La selección guardada difiere de los MAE de validación.")

    predicciones = pd.read_parquet(carpeta / "predicciones.parquet")
    prueba = leer_particion(manifiesto, "prueba").rename(columns={OBJETIVO: "real"})
    columnas = [*CLAVES_PARES, "nivel_t", "gestion_t", "matricula_t", "real"]
    if set(predicciones.modelo) != MODELOS.keys():
        raise ValueError("No están los tres comparadores en las predicciones.")
    if (
        not np.isfinite(predicciones[["predicho", "error"]]).to_numpy().all()
        or predicciones.predicho.lt(0).any()
        or not np.array_equal(predicciones.error, predicciones.predicho - predicciones.real)
    ):
        raise ValueError("Las predicciones guardadas contienen valores o errores incompatibles.")
    cortes_esperados = np.select(
        [predicciones.matricula_t.lt(10), predicciones.matricula_t.lt(50), predicciones.matricula_t.lt(200)],
        ["1–9", "10–49", "50–199"], default="200 o más",
    )
    if not np.array_equal(predicciones.tamano, cortes_esperados):
        raise ValueError("Los tamaños de servicio difieren de los intervalos del protocolo.")

    totales, cortes = [], []
    for modelo, tabla in predicciones.groupby("modelo"):
        _comparar_tablas(tabla[columnas], prueba[columnas], CLAVES_PARES)
        if modelo == "persistencia" and not np.array_equal(tabla.predicho, tabla.matricula_t):
            raise ValueError("Persistencia difiere de la matrícula de entrada.")
        totales.append({"modelo": modelo, **_calcular(tabla.real, tabla.predicho)})
        for dimension in ("nivel_t", "tamano"):
            for segmento, filas in tabla.groupby(dimension):
                cortes.append({"modelo": modelo, "dimension": dimension, "segmento": segmento,
                               **_calcular(filas.real, filas.predicho)})

    globales = pd.DataFrame(totales, columns=["modelo", *METRICAS])
    _comparar_tablas(globales, pd.read_csv(carpeta / "metricas_prueba.csv"), ["modelo"])
    _comparar_tablas(globales, pd.DataFrame(resumen["metricas_prueba"]), ["modelo"])
    _comparar_tablas(pd.DataFrame(cortes), pd.read_csv(carpeta / "metricas_segmentos.csv"),
                    ["modelo", "dimension", "segmento"])
    evidencia = {
        "fecha": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "ejecucion": carpeta.relative_to(ROOT).as_posix(),
        "sha256_panel": huella_panel, "huellas_verificadas": len(huellas),
        "predicciones_verificadas": len(predicciones), "pares_por_modelo": len(prueba),
        "grupos_modelo_segmento_verificados": len(cortes), "configuraciones_validadas": len(validacion),
        "modelo_seleccionado": elegido, "segundos_entrenamiento_y_evaluacion": resumen["segundos_ejecucion"],
        "metricas_verificadas": globales.to_dict(orient="records"),
    }
    salida = ROOT / "results" / "verificacion_ejecucion_ml.json"
    salida.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2, allow_nan=False) + "\n", "utf-8")
    print(f"{len(predicciones)} predicciones, {len(cortes)} cortes y {len(huellas)} huellas verificados.")
    return globales.set_index("modelo").loc[list(MODELOS)]


def exportar_figura(metricas):
    cache = ROOT / "data" / "ml" / "matplotlib"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figura, eje = plt.subplots(figsize=(9, 4.5), layout="constrained")
    colores = ["#087B68", "#386A9B", "#AA641A"]
    etiquetas = [MODELOS[modelo] for modelo in metricas.index]
    barras = eje.barh(etiquetas, metricas.mae, color=colores, height=0.55)
    eje.invert_yaxis()
    eje.bar_label(barras, labels=[f"{x:.2f}".replace(".", ",") for x in metricas.mae], padding=7)
    eje.set_xlim(0, metricas.mae.max() * 1.12)
    eje.set_xlabel("Error absoluto medio (matrículas por servicio)")
    eje.set_title("Evaluación histórica de la matrícula de 2024", loc="left", weight="bold", pad=30)
    eje.text(0, 1.02, f"{int(metricas.n.iloc[0]):,} pares por modelo".replace(",", " "),
             transform=eje.transAxes, color="#4B6178")
    eje.spines[["top", "right", "left"]].set_visible(False)
    eje.xaxis.grid(color="#DFE7EF")
    eje.set_axisbelow(True)
    salida = ROOT / "evidence" / "comparacion_mae_2024.png"
    figura.savefig(salida, dpi=240, facecolor="white")
    plt.close(figura)
    print(f"Figura exportada a {salida.relative_to(ROOT)} con Matplotlib {matplotlib.__version__}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figura", action="store_true", help="Exporta el gráfico PNG con Matplotlib.")
    args = parser.parse_args()
    metricas = auditar()
    if args.figura:
        exportar_figura(metricas)


if __name__ == "__main__":
    main()

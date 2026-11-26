"""Métricas de regresión y cortes por nivel y tamaño de servicio."""

import numpy as np
import pandas as pd


TAMANOS = ("1–9", "10–49", "50–199", "200 o más")


def metricas(real, predicho):
    real = np.asarray(real, dtype=np.float64)
    predicho = np.asarray(predicho, dtype=np.float64)
    if real.shape != predicho.shape or real.ndim != 1 or not real.size:
        raise ValueError("Las series de evaluación deben tener el mismo tamaño positivo.")
    if not np.isfinite(real).all() or not np.isfinite(predicho).all():
        raise ValueError("Las series de evaluación contienen valores no finitos.")
    error = predicho - real
    absoluto = np.abs(error)
    sse = float(np.dot(error, error))
    centrado = real - real.mean()
    sst = float(np.dot(centrado, centrado))
    total = float(real.sum())
    return {
        "n": int(real.size), "mae": float(absoluto.mean()), "rmse": float(np.sqrt(sse / real.size)),
        "r2": 1 - sse / sst if sst else None,
        "wape": 100 * float(absoluto.sum()) / total if total > 0 else None,
    }


def tamanos(matricula_entrada):
    return pd.cut(matricula_entrada, bins=(0, 9, 49, 199, np.inf), labels=TAMANOS).astype("string")


def metricas_segmentadas(predicciones):
    grupos = []
    for dimension in ("nivel_t", "tamano"):
        for (modelo, segmento), filas in predicciones.groupby(["modelo", dimension], sort=True):
            grupos.append({
                "modelo": modelo, "dimension": dimension, "segmento": segmento,
                **metricas(filas.real, filas.predicho),
            })
    return grupos

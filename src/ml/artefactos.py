"""Ubicación y validación de los archivos locales para evaluación."""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from src.ml.panel import OBJETIVO, PARTICIONES, PREDICTORES_BASE, PREDICTORES_TASAS


ROOT = Path(__file__).resolve().parents[2]
MANIFIESTO = ROOT / "results" / "panel_ml.json"
PROTOCOLO = 1
MODELOS = {"persistencia": "Persistencia", "ridge": "Ridge", "hgb": "HistGradientBoosting"}
METRICAS = ("n", "mae", "rmse", "r2", "wape")
CLAVES_PARES = ["anio_t", "anio_t1", "cod_mod", "anexo"]
COLUMNAS_PARES = [*CLAVES_PARES, *PREDICTORES_BASE, *PREDICTORES_TASAS, OBJETIVO]


def sha256_archivo(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def directorio_ejecucion(manifiesto):
    huella = manifiesto["sha256_panel_canonico"]
    if not re.fullmatch("[0-9a-f]{64}", huella):
        raise ValueError("La huella del panel no es válida.")
    return ROOT / "results" / "ml" / f"v{PROTOCOLO}_{huella[:16]}"


def ruta_particion(manifiesto, nombre):
    artefacto = manifiesto["artefactos"][nombre]
    ruta = (ROOT / artefacto["archivo"]).resolve()
    if not ruta.is_relative_to(ROOT / "data" / "ml"):
        raise ValueError(f"La partición {nombre} debe estar bajo data/ml.")
    if sha256_archivo(ruta) != artefacto["sha256"]:
        raise ValueError(f"La huella de {nombre} no coincide con el panel preparado.")
    return ruta


def leer_particion(manifiesto, nombre):
    pares = pd.read_parquet(ruta_particion(manifiesto, nombre))
    anio = PARTICIONES[nombre]
    esperado = manifiesto["particiones"][nombre]["pares"]
    if (
        list(pares.columns) != COLUMNAS_PARES
        or len(pares) != esperado
        or pares.empty
        or not pares.anio_t.eq(anio).all()
        or not pares.anio_t1.eq(anio + 1).all()
        or pares[CLAVES_PARES].isna().to_numpy().any()
        or pares.duplicated(["cod_mod", "anexo"]).any()
        or pares[OBJETIVO].isna().any()
        or pares[OBJETIVO].le(0).any()
        or pares.matricula_t.isna().any()
        or pares.matricula_t.le(0).any()
    ):
        raise ValueError(f"La partición {nombre} no cumple el contrato temporal.")
    return pares

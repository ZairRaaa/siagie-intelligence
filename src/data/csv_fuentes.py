"""Resumen de matrícula de los CSV identificados en el manifiesto del SIAGIE."""

import hashlib
import json
from pathlib import Path

import pandas as pd


FUENTES = Path(__file__).resolve().parents[2] / "contexto"


def resumen_anual_csv():
    manifiesto = json.loads(
        (FUENTES / "resultados" / "manifiesto_fuentes.json").read_text("utf-8-sig")
    )
    resumen = []
    for fuente in sorted(manifiesto["fuentes"], key=lambda fuente: fuente["anio"]):
        ruta = FUENTES / fuente["archivo"]
        with ruta.open("rb") as archivo:
            huella = hashlib.file_digest(archivo, "sha256").hexdigest()
            if huella != fuente["sha256"]:
                raise ValueError(f"La huella no coincide con el manifiesto: {ruta.name}.")
            archivo.seek(0)
            totales = pd.read_csv(
                archivo, encoding="utf-8-sig", usecols=["TotalEstudiantes"],
                dtype={"TotalEstudiantes": "int64"},
            )["TotalEstudiantes"]
        if len(totales) != fuente["filas"]:
            raise ValueError(f"El número de filas no coincide con el manifiesto: {ruta.name}.")
        resumen.append({
            "anio": fuente["anio"], "filas": len(totales), "matricula": int(totales.sum()),
        })
    return resumen

"""Verifica las fuentes, concilia el panel con SQL Server y fija las particiones."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import pandas as pd
import pyarrow

from src.ml.artefactos import sha256_archivo
from src.ml.panel import (
    OBJETIVO, PARTICIONES, PREDICTORES_BASE, PREDICTORES_TASAS, VERSION_PREPARACION,
    construir_pares, leer_panel_csv, leer_panel_dw,
)


ROOT = Path(__file__).resolve().parents[1]
DIRECTORIO = ROOT / "data" / "ml"
EVIDENCIA = ROOT / "results" / "panel_ml.json"


def guardar_particiones(panel, panel_sha):
    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO / f"v{VERSION_PREPARACION}_{panel_sha[:16]}"
    with TemporaryDirectory(dir=DIRECTORIO) as temporal:
        preparacion = Path(temporal) / destino.name
        preparacion.mkdir()
        panel.to_parquet(preparacion / "panel.parquet", index=False)
        cobertura = {}
        for nombre, anio in PARTICIONES.items():
            pares, cobertura[nombre] = construir_pares(panel, anio)
            if pares.empty:
                raise ValueError(f"La partición {nombre} no contiene pares.")
            pares.to_parquet(preparacion / f"{nombre}.parquet", index=False)
        huellas = {generado.name: sha256_archivo(generado) for generado in preparacion.iterdir()}
        if not destino.exists():
            try:
                preparacion.rename(destino)
            except FileExistsError:
                # Otro proceso publicó esta versión antes de que acabara la preparación.
                pass
        archivos = {}
        for nombre, huella in sorted(huellas.items()):
            final = destino / nombre
            if not final.is_file() or huella != sha256_archivo(final):
                raise ValueError(f"El artefacto ya publicado no coincide: {final}.")
            archivos[final.stem] = {"archivo": final.relative_to(ROOT).as_posix(), "sha256": huella}
    return archivos, cobertura


def preparar(ruta_dw):
    panel, huellas = leer_panel_csv()
    panel_sha = hashlib.sha256(panel.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()
    if ruta_dw is None:
        referencia = json.loads(EVIDENCIA.read_text("utf-8"))
        if referencia["sha256_panel_canonico"] != panel_sha:
            raise ValueError("El panel CSV difiere de la versión histórica conciliada.")
        archivos, cobertura = guardar_particiones(panel, panel_sha)
        if archivos != referencia["artefactos"] or cobertura != referencia["particiones"]:
            raise ValueError("Las particiones regeneradas difieren de la referencia publicada.")
        print(f"{len(panel)} filas verificadas contra la huella histórica. Particiones regeneradas.")
        return
    dw, huellas_dw = leer_panel_dw(ruta_dw)
    if huellas != huellas_dw:
        raise ValueError("Los lotes del DW y la copia CSV corresponden a huellas distintas.")
    try:
        pd.testing.assert_frame_equal(panel, dw)
    except AssertionError as error:
        raise ValueError("Hay diferencias entre el DW y el CSV en las filas del panel.") from error

    archivos, cobertura = guardar_particiones(panel, panel_sha)
    anual = [
        {"anio": int(anio), "servicios": len(grupo), "filas_fuente": int(grupo.filas.sum()),
         "matricula": int(grupo.matricula.sum()), "sha256_fuente": huellas[anio]}
        for anio, grupo in panel.groupby("anio", sort=True)
    ]
    evidencia = {
        "fecha": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "version_preparacion": VERSION_PREPARACION,
        "fuente": "CSV SIAGIE verificados, con panel conciliado mediante SQLCMD",
        "conciliacion": {"filas": len(panel), "columnas": panel.columns.tolist(),
                         "sha256_exportacion_dw": sha256_archivo(ruta_dw)},
        "sha256_panel_canonico": panel_sha,
        "versiones": {"pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "anual": anual, "particiones": cobertura, "artefactos": archivos,
        "predictores_base": PREDICTORES_BASE, "predictores_tasas_candidatos": PREDICTORES_TASAS,
        "objetivo": OBJETIVO,
    }
    with TemporaryDirectory(dir=EVIDENCIA.parent) as directorio:
        temporal = Path(directorio) / EVIDENCIA.name
        temporal.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", "utf-8")
        temporal.replace(EVIDENCIA)
    print(f"{len(panel)} filas del panel conciliadas. Artefactos en {DIRECTORIO.relative_to(ROOT)}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origen = parser.add_mutually_exclusive_group(required=True)
    origen.add_argument("--dw", type=Path, help="Salida UTF-16 de SQLCMD para una nueva conciliación.")
    origen.add_argument("--solo-csv", action="store_true", help="Regenera los archivos de la referencia conciliada.")
    args = parser.parse_args()
    preparar(args.dw)


if __name__ == "__main__":
    main()

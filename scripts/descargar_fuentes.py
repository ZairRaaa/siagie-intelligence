"""Descarga y verifica los CSV oficiales del SIAGIE publicados por MINEDU."""

import argparse
import hashlib
import json
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile, TemporaryFile
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FUENTES = ROOT / "contexto"
PORTAL = "https://www.datosabiertos.gob.pe/sites/default/files/"
PUBLICACION = "https://github.com/ZairRaaa/siagie-intelligence/releases/download/v1.0.0/siagie-minedu-2021-2024.zip"


def verificar(ruta, fuente):
    if ruta.stat().st_size != fuente["bytes"]:
        raise ValueError(f"El tamaño de {fuente['archivo']} difiere del manifiesto.")
    with ruta.open("rb") as archivo:
        if hashlib.file_digest(archivo, "sha256").hexdigest() != fuente["sha256"]:
            raise ValueError(f"La huella SHA-256 de {fuente['archivo']} difiere del manifiesto.")


def guardar(entrada, fuente):
    nombre = fuente["archivo"]
    destino = FUENTES / nombre
    with NamedTemporaryFile(dir=FUENTES, suffix=".descarga", delete=False) as temporal:
        ruta = Path(temporal.name)
    try:
        with ruta.open("wb") as salida:
            bytes_leidos = 0
            while bloque := entrada.read(2**20):
                bytes_leidos += len(bloque)
                if bytes_leidos > fuente["bytes"]:
                    raise ValueError(f"El portal devolvió un archivo más grande de lo esperado: {nombre}")
                salida.write(bloque)
        verificar(ruta, fuente)
        try:
            ruta.rename(destino)
        except FileExistsError:
            verificar(destino, fuente)
    finally:
        ruta.unlink(missing_ok=True)
    print(f"{fuente['anio']}: CSV y huella verificados", flush=True)


def leer_zip(archivo, faltantes):
    with ZipFile(archivo) as paquete:
        for fuente in faltantes:
            with paquete.open(fuente["archivo"]) as entrada:
                guardar(entrada, fuente)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origen = parser.add_mutually_exclusive_group()
    origen.add_argument("--zip", type=Path, help="Lee el paquete descargado anteriormente.")
    origen.add_argument("--portal", action="store_true", help="Descarga directamente del portal MINEDU.")
    args = parser.parse_args()
    manifiesto = json.loads((FUENTES / "resultados/manifiesto_fuentes.json").read_text("utf-8-sig"))
    faltantes = []
    try:
        for fuente in manifiesto["fuentes"]:
            ruta = FUENTES / fuente["archivo"]
            if ruta.is_file():
                verificar(ruta, fuente)
                print(f"{fuente['anio']}: archivo local verificado", flush=True)
            else:
                faltantes.append(fuente)
        if not faltantes:
            return 0
        if args.zip:
            leer_zip(args.zip, faltantes)
        elif args.portal:
            for fuente in faltantes:
                print(f"{fuente['anio']}: descargando del portal oficial", flush=True)
                with urlopen(PORTAL + quote(fuente["archivo"]), timeout=30) as entrada:
                    guardar(entrada, fuente)
        else:
            print("Descargando el paquete publicado en GitHub…", flush=True)
            with TemporaryFile() as archivo, urlopen(PUBLICACION, timeout=30) as entrada:
                copyfileobj(entrada, archivo, length=2**20)
                archivo.seek(0)
                leer_zip(archivo, faltantes)
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        print(f"{error}. Revisa la descarga y las instrucciones del README.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Construye una copia SQLite derivada de las fuentes originales verificadas."""

import csv
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from decimal import Decimal
from io import TextIOWrapper
from itertools import batched
from tempfile import NamedTemporaryFile

from sqlalchemy import URL, create_engine, event

from src.data.contrato import DIMENSIONES, MEDIDAS_CSV
from src.data.csv_fuentes import FUENTES


DIRECTORIO_CACHE = FUENTES.parent / "data"
VERSION_CACHE = 1


def localizar_cache():
    ruta_manifiesto = FUENTES / "resultados" / "manifiesto_fuentes.json"
    contenido = ruta_manifiesto.read_bytes()
    version = hashlib.sha256(contenido).hexdigest()
    ruta = DIRECTORIO_CACHE / f"siagie_{VERSION_CACHE}_{version}.sqlite"
    return ruta, json.loads(contenido.decode("utf-8-sig"))


def rango_edad(edad):
    if edad is None:
        return "Desconocida"
    for limite, etiqueta in ((2, "0-2"), (5, "3-5"), (11, "6-11"), (16, "12-16")):
        if edad <= limite:
            return etiqueta
    return "17-18"


def normalizar_fila(anio, fila):
    edad = Decimal(fila["Edad"]) if fila["Edad"].strip() else None
    if edad is not None:
        if edad != int(edad):
            raise ValueError(f"Se esperaba una edad entera en {anio}, se obtuvo {edad}.")
        edad = int(edad)
    dimensiones = (
        anio, fila["cod_mod"].zfill(7), fila["anexo"].zfill(3), fila["Nombre"].strip(),
        fila["id_nivel"], fila["dsc_nivel"].strip(), fila["gestion"].strip(),
        edad, rango_edad(edad), fila["TipoDiscaIntegrada"].strip() or "Sin discapacidad registrada",
    )
    return dimensiones + tuple(int(fila[c]) if c in fila else None for c in MEDIDAS_CSV.values())


def cargar_periodo(conexion, fuente):
    ruta = FUENTES / fuente["archivo"]
    anio = fuente["anio"]
    marcadores = ", ".join("?" for _ in (*DIMENSIONES, *MEDIDAS_CSV))
    filas = 0
    with ruta.open("rb") as archivo:
        huella = hashlib.file_digest(archivo, "sha256").hexdigest()
        if huella != fuente["sha256"]:
            raise ValueError(f"La huella no coincide con el manifiesto: {ruta.name}.")
        archivo.seek(0)
        with TextIOWrapper(archivo, encoding="utf-8-sig", newline="") as contenido:
            lector = csv.DictReader(contenido)
            if lector.fieldnames != fuente["columnas"]:
                raise ValueError(f"El encabezado cambió: {ruta.name}.")
            registros = (normalizar_fila(anio, fila) for fila in lector)
            for bloque in batched(registros, 10_000):
                conexion.executemany(f"INSERT INTO matricula VALUES ({marcadores})", bloque)
                filas += len(bloque)
    if filas != fuente["filas"]:
        raise ValueError(f"El número de filas cambió: {ruta.name}.")
    conexion.execute("INSERT INTO periodos VALUES (?, ?, ?, ?, ?)", (
        anio, "PromocionGuiada" in lector.fieldnames, "Desaprobado" in lector.fieldnames,
        huella, None,
    ))
    return filas


def preparar_cache():
    ruta, manifiesto = localizar_cache()
    if ruta.is_file():
        return ruta
    ruta.parent.mkdir(exist_ok=True)
    with NamedTemporaryFile(dir=ruta.parent, suffix=".sqlite", delete=False) as archivo:
        temporal = ruta.parent / os.path.basename(archivo.name)
    try:
        with closing(sqlite3.connect(temporal)) as conexion, conexion:
            columnas = [
                f"{campo} {'INTEGER' if campo in ('anio', 'edad') else 'TEXT'}"
                for campo in DIMENSIONES
            ]
            columnas.extend(f"{campo} INTEGER" for campo in MEDIDAS_CSV)
            conexion.execute(f"CREATE TABLE matricula ({', '.join(columnas)})")
            conexion.execute("""
                CREATE TABLE periodos (
                    anio INTEGER PRIMARY KEY, disp_promocion INTEGER NOT NULL,
                    disp_desaprobacion INTEGER NOT NULL, huella TEXT NOT NULL, actualizado TEXT
                )
            """)
            for fuente in manifiesto["fuentes"]:
                cargar_periodo(conexion, fuente)
            conexion.execute("CREATE INDEX ix_servicio ON matricula (cod_mod, anexo, anio)")
            conexion.execute("CREATE INDEX ix_nivel ON matricula (anio, nivel, gestion)")
        if not ruta.exists():
            try:
                temporal.rename(ruta)
            except FileExistsError:
                # Otro proceso publicó la misma versión completa mientras se construía.
                pass
        return ruta
    finally:
        temporal.unlink(missing_ok=True)


def crear_motor_csv():
    ruta = preparar_cache()
    uri = ruta.resolve().as_uri()
    motor = create_engine(URL.create(
        "sqlite+pysqlite", database=uri, query={"uri": "true", "mode": "ro"},
    ))

    @event.listens_for(motor, "connect")
    def registrar_lower(conexion, _):
        conexion.create_function("lower", 1, str.casefold, deterministic=True)

    return motor

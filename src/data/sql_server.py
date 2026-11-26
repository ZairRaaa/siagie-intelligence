"""Configuración y primeras consultas de lectura a SQL Server."""

import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[2]
RESUMEN_ANUAL = text("""
    SELECT anio, COUNT_BIG(*) AS filas,
           SUM(CONVERT(bigint, total_estudiantes)) AS matricula
    FROM dw.FactMatricula
    GROUP BY anio
    ORDER BY anio
""")


def crear_motor():
    load_dotenv(ROOT / ".env", interpolate=False)
    opciones = {
        "Driver": os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server"),
        "Server": os.getenv("SQL_SERVER", "").strip(),
        "Database": os.getenv("SQL_DATABASE", "DW_SIAGIE").strip(),
        "Trusted_Connection": os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower(),
        "Encrypt": os.getenv("SQL_ENCRYPT", "yes").lower(),
        "TrustServerCertificate": os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "no").lower(),
    }
    if not opciones["Server"] or not opciones["Database"]:
        raise ValueError("Define SQL_SERVER y SQL_DATABASE en .env.")
    if opciones["Trusted_Connection"] != "yes":
        raise ValueError("La conexión usa autenticación integrada de Windows.")
    for campo in ("Encrypt", "TrustServerCertificate"):
        if opciones[campo] not in {"yes", "no"}:
            raise ValueError(f"{campo} debe ser yes o no.")
    if opciones["Driver"] not in pyodbc.drivers():
        raise ValueError(f"Controlador ODBC no instalado: {opciones['Driver']}.")
    for campo, valor in opciones.items():
        if any(caracter in valor for caracter in ";{}\x00\r\n"):
            raise ValueError(f"Valor inválido para {campo}.")

    cadena = ";".join(
        f"{campo}={{{valor}}}" if campo == "Driver" else f"{campo}={valor}"
        for campo, valor in opciones.items()
    )
    url = URL.create("mssql+pyodbc", query={"odbc_connect": cadena})
    return create_engine(url, pool_pre_ping=True, connect_args={"timeout": 8})


def resumen_anual_sql():
    motor = crear_motor()
    try:
        with motor.connect() as conexion:
            return [dict(fila) for fila in conexion.execute(RESUMEN_ANUAL).mappings()]
    finally:
        motor.dispose()

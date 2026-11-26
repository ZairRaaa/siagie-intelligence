"""Panel anual y transiciones supervisadas de matrícula por servicio."""

import pandas as pd
from sqlalchemy import text

from src.data.cache_csv import crear_motor_csv
from src.data.consultas import PERIODOS


ANIOS = (2021, 2022, 2023, 2024)
CLAVE = ["cod_mod", "anexo"]
CLAVE_ANUAL = ["anio", *CLAVE]
CONTEOS = ["filas", "matricula", "aprobados", "retirados", "total_atraso"]
COLUMNAS = [*CLAVE_ANUAL, "nivel", "gestion", *CONTEOS]
TIPOS = {c: "string" if c in {*CLAVE, "nivel", "gestion"} else "int64" for c in COLUMNAS}
PARTICIONES = {"entrenamiento": 2021, "validacion": 2022, "prueba": 2023}
PREDICTORES_BASE = ["matricula_t", "nivel_t", "gestion_t"]
PREDICTORES_TASAS = ["tasa_aprobados_t", "tasa_retirados_t", "tasa_total_atraso_t"]
OBJETIVO = "matricula_t1"
VERSION_PREPARACION = 1

PANEL_CSV = text("""
    SELECT anio,cod_mod,anexo,nivel,gestion,COUNT(*) AS filas,
           SUM(matricula) AS matricula,SUM(aprobados) AS aprobados,
           SUM(retirados) AS retirados,SUM(total_atraso) AS total_atraso
    FROM matricula
    WHERE anio BETWEEN 2021 AND 2024
    GROUP BY anio,cod_mod,anexo,nivel,gestion
    ORDER BY anio,cod_mod,anexo
""")


def validar_panel(panel):
    if list(panel.columns) != COLUMNAS:
        raise ValueError("Las columnas del panel no coinciden con el contrato.")
    if panel.isna().to_numpy().any():
        raise ValueError("Hay valores ausentes en el panel.")
    if panel.duplicated(CLAVE_ANUAL).any():
        raise ValueError("Hay más de un registro para un mismo servicio y año.")
    if set(panel["anio"]) != set(ANIOS):
        raise ValueError("El panel debe cubrir 2021–2024.")
    if not panel.cod_mod.str.fullmatch("[0-9]{7}").all() or not panel.anexo.str.fullmatch("[0-9]{3}").all():
        raise ValueError("Códigos modulares o anexos fuera de su formato.")
    if (panel[["nivel", "gestion"]].apply(lambda serie: serie.str.strip()) == "").to_numpy().any():
        raise ValueError("Hay niveles o gestiones sin valor.")
    if panel[["filas", "matricula"]].le(0).to_numpy().any():
        raise ValueError("Se esperaban filas y matrícula positivas en el panel observado.")
    medidas = panel[CONTEOS[2:]]
    if medidas.lt(0).to_numpy().any() or medidas.gt(panel.matricula, axis=0).to_numpy().any():
        raise ValueError("Una medida es negativa o supera su matrícula.")


def leer_panel_csv():
    motor = crear_motor_csv()
    try:
        with motor.connect() as conexion:
            huellas = {
                fila.anio: fila.huella for fila in conexion.execute(PERIODOS["csv"]) if fila.anio in ANIOS
            }
            panel = pd.read_sql_query(PANEL_CSV, conexion, dtype=TIPOS)
    finally:
        motor.dispose()
    validar_panel(panel)
    return panel, huellas


def leer_panel_dw(ruta):
    with ruta.open(encoding="utf-16") as archivo:
        if archivo.readline().strip() != "LOTES":
            raise ValueError("La salida SQLCMD debe comenzar con LOTES.")
        huellas = {}
        for linea in archivo:
            if linea.strip() == "PANEL":
                break
            anio, huella = linea.strip().split("|")
            huellas[int(anio)] = huella
        else:
            raise ValueError("No se encontró la sección PANEL en el archivo SQLCMD.")
        panel = pd.read_csv(archivo, sep="|", header=None, names=COLUMNAS, dtype=TIPOS, keep_default_na=False)
    validar_panel(panel)
    return panel.sort_values(CLAVE_ANUAL, ignore_index=True), huellas


def construir_pares(panel, anio):
    actual = panel.loc[panel.anio.eq(anio)].rename(columns={
        "matricula": "matricula_t", "nivel": "nivel_t", "gestion": "gestion_t",
    })
    siguiente = panel.loc[panel.anio.eq(anio + 1), [*CLAVE, "matricula", "nivel", "gestion"]]
    siguiente = siguiente.rename(columns={"matricula": OBJETIVO})
    pares = actual.merge(siguiente, on=CLAVE, how="inner", validate="one_to_one")
    pares = pares.rename(columns={"anio": "anio_t"}).assign(anio_t1=anio + 1)
    for medida, tasa in zip(CONTEOS[2:], PREDICTORES_TASAS, strict=True):
        pares[tasa] = 100 * pares[medida] / pares.matricula_t
    cobertura = {
        "anio_t": anio, "anio_t1": anio + 1,
        "servicios_origen": len(actual), "servicios_destino": len(siguiente), "pares": len(pares),
        "sin_etiqueta": len(actual) - len(pares), "sin_antecedente_inmediato": len(siguiente) - len(pares),
        "cobertura_origen_pct": 100 * len(pares) / len(actual),
        "cambio_nivel": int(pares.nivel_t.ne(pares.nivel).sum()),
        "cambio_gestion": int(pares.gestion_t.ne(pares.gestion).sum()),
        "pares_matricula_t_menor_10": int(pares.matricula_t.lt(10).sum()),
    }
    columnas = ["anio_t", "anio_t1", *CLAVE, *PREDICTORES_BASE, *PREDICTORES_TASAS, OBJETIVO]
    return pares[columnas].reset_index(drop=True), cobertura

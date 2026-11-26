"""Concilia los agregados de Python sobre CSV con el mismo SQL ejecutado en el DW."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.dialects import mssql

from src.analytics.indicadores import aplicar_indicadores, variaciones_anuales
from src.data.consultas import PERIODOS, consulta_agregados
from src.data.contrato import Filtros, MEDIDAS_CSV
from src.data.fuente_analitica import FuenteAnalitica


CASOS = {
    "anual": (Filtros(), ("anio",)),
    "total": (Filtros(), ()),
    "nivel_gestion": (Filtros(), ("anio", "nivel", "gestion")),
    "primaria_publica": (
        Filtros(anios=(2023, 2024), niveles=("B0",), gestiones=("Pública de gestión directa",)),
        ("anio",),
    ),
    "servicio": (Filtros(servicio=("0001506", "000")), ("anio", "cod_mod", "anexo")),
    "edad_y_tipo": (
        Filtros(edades=(None, 0), discapacidades=("Sin discapacidad registrada", "Sin especificacion")),
        ("anio", "edad", "rango_edad", "tipo_discapacidad"),
    ),
    "vacio": (Filtros(anios=()), ()),
}


def preparar_sql(ruta):
    consultas = {"periodos": PERIODOS["sql"]}
    consultas.update({
        nombre: consulta_agregados("sql", filtros, por)
        for nombre, (filtros, por) in CASOS.items()
    })
    consultas["vista_anual"] = text("""
        SELECT anio, filas_hechos, matricula, aprobados, retirados, atraso,
               promocion_guiada, desaprobados
        FROM dw.vw_ResumenAnual ORDER BY anio
    """)
    consultas["vista_nivel_gestion"] = text("""
        SELECT anio, codigo_nivel, gestion, matricula, aprobados, retirados, atraso,
               promocion_guiada, desaprobados
        FROM dw.vw_MatriculaNivelGestion ORDER BY anio, codigo_nivel, gestion
    """)
    partes = ["SET NOCOUNT ON;\nGO"]
    for nombre, consulta in consultas.items():
        sql = consulta.compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True})
        partes.append(f"PRINT 'CASO:{nombre}';\n{sql};\nGO")
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(partes) + "\n", encoding="utf-8")


def leer_sql(ruta):
    secciones = {}
    for linea in ruta.read_text(encoding="utf-16").splitlines():
        if linea.startswith("CASO:"):
            secciones[linea.removeprefix("CASO:")] = []
        elif linea.strip():
            secciones[next(reversed(secciones))].append(linea.split("|"))
    return secciones


def verificar(ruta_sql, salida):
    datos_sql = leer_sql(ruta_sql)
    datos_csv = {}
    evidencia = {}
    with FuenteAnalitica("csv") as fuente:
        catalogo = fuente.periodos()
        for nombre, (filtros, por) in CASOS.items():
            inicio = perf_counter()
            datos_csv[nombre] = fuente.agregados(filtros, por)
            evidencia[nombre] = {
                "grupos": len(datos_csv[nombre]),
                "segundos_csv": round(perf_counter() - inicio, 3),
            }
    columnas_periodos = tuple(catalogo[0])
    assert [(str(f["anio"]), f["huella"]) for f in catalogo] == [
        (fila[0], fila[3]) for fila in datos_sql["periodos"]
    ], "Los lotes SQL y los CSV tienen huellas distintas."

    periodos_sql = {}
    for fila in datos_sql["periodos"]:
        anio, promocion, desaprobacion, huella, actualizado = fila
        periodos_sql[int(anio)] = dict(zip(columnas_periodos, (
            int(anio), int(promocion), int(desaprobacion), huella, actualizado,
        ), strict=True))

    for nombre, (filtros, por) in CASOS.items():
        numericos = set(MEDIDAS_CSV) | {"anio", "edad", "filas", "servicios"}
        columnas = (*por, "filas", "servicios", *MEDIDAS_CSV)
        filas = [
            {clave: None if valor == "NULL" else int(valor) if clave in numericos else valor
             for clave, valor in zip(columnas, fila, strict=True)}
            for fila in datos_sql[nombre]
        ]
        anios = tuple(periodos_sql) if filtros.anios is None else filtros.anios
        indicadores_sql = aplicar_indicadores(filas, periodos_sql, anios)
        orden = lambda fila: tuple(str(fila[c]) for c in por)
        if sorted(datos_csv[nombre], key=orden) != sorted(indicadores_sql, key=orden):
            raise AssertionError(f"Los agregados SQL y CSV difieren en {nombre}.")
        evidencia[nombre]["conciliado"] = True
        print(f"{nombre}: {len(indicadores_sql)} grupos conciliados")

    columnas_vistas = {
        "anual": ("anio", "filas"),
        "nivel_gestion": ("anio", "nivel", "gestion"),
    }
    medidas_vistas = (
        "matricula", "aprobados", "retirados", "total_atraso", "promocion_guiada", "desaprobados",
    )
    for nombre, dimensiones in columnas_vistas.items():
        columnas = (*dimensiones, *medidas_vistas)
        previsto = [
            ["NULL" if fila[clave] is None else str(fila[clave]) for clave in columnas]
            for fila in datos_csv[nombre]
        ]
        vista = f"vista_{nombre}"
        if sorted(previsto) != sorted(datos_sql[vista]):
            raise AssertionError(f"El resultado difiere de la vista HEFESTO {vista}.")
        evidencia[vista] = {"grupos": len(previsto), "conciliado": True}
        print(f"{vista}: {len(previsto)} grupos conciliados")

    salida.write_text(json.dumps({
        "fecha": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "metodo": "Consultas del módulo analítico compiladas y ejecutadas con SQLCMD, comparadas con CSV.",
        "version_origen": catalogo,
        "casos": evidencia,
        "indicadores_anuales": variaciones_anuales(datos_csv["anual"]),
        "indicadores_periodo_completo": datos_csv["total"][0],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="accion", required=True)
    generar = sub.add_parser("preparar")
    generar.add_argument("archivo", type=Path)
    conciliar = sub.add_parser("comparar")
    conciliar.add_argument("archivo", type=Path)
    conciliar.add_argument("salida", type=Path)
    args = parser.parse_args()
    if args.accion == "preparar":
        preparar_sql(args.archivo)
    else:
        verificar(args.archivo, args.salida)


if __name__ == "__main__":
    main()

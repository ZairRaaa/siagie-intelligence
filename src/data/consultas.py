"""Consultas analíticas de lectura, con valores enlazados como parámetros."""

from sqlalchemy import Integer, Unicode, bindparam, text

from src.data.contrato import DIMENSIONES, DISPONIBILIDAD, MEDIDAS_CSV


PERIODOS = {
    "sql": text("""
        SELECT a.anio, a.disp_promocion, a.disp_desaprobacion, RTRIM(l.sha256) AS huella,
               CONVERT(varchar(33), l.fin_utc, 126) AS actualizado
        FROM dw.DimAnio AS a
        LEFT JOIN etl.Lote AS l ON l.anio=a.anio AND l.estado='COMPLETADO'
        ORDER BY a.anio
    """),
    "csv": text("SELECT * FROM periodos ORDER BY anio"),
}

_CAMPOS_SQL = (
    "f.anio", "s.cod_mod", "s.anexo", "s.nombre", "n.codigo", "n.descripcion",
    "s.gestion", "e.edad", "e.rango", "d.tipo",
)
_COLUMNAS_SQL = ", ".join((
    *(f"{campo} AS {alias}" for campo, alias in zip(_CAMPOS_SQL, DIMENSIONES, strict=True)),
    "f.total_estudiantes AS matricula",
    *(f"f.{campo}" for campo in MEDIDAS_CSV if campo != "matricula"),
))
_RELACIONES_SQL = f"""(
    SELECT {_COLUMNAS_SQL}
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos
"""
TABLAS = {"sql": _RELACIONES_SQL, "csv": "matricula"}


def _condiciones(filtros):
    condiciones, parametros = [], []
    for campo, valores, tipo in (
        ("anio", filtros.anios, Integer()),
        ("nivel", filtros.niveles, Unicode()),
        ("gestion", filtros.gestiones, Unicode()),
        ("edad", filtros.edades, Integer()),
        ("tipo_discapacidad", filtros.discapacidades, Unicode()),
    ):
        if valores is None:
            continue
        conocidos = tuple(valor for valor in valores if valor is not None)
        alternativas = []
        if conocidos:
            alternativas.append(f"{campo} IN :{campo}")
            parametros.append(bindparam(campo, conocidos, expanding=True, type_=tipo))
        if campo == "edad" and None in valores:
            alternativas.append("edad IS NULL")
        condiciones.append("(" + (" OR ".join(alternativas) or "1=0") + ")")

    if filtros.servicio is not None:
        codigo, anexo = filtros.servicio
        condiciones.extend(("cod_mod=:cod_mod", "anexo=:anexo"))
        parametros.extend((
            bindparam("cod_mod", codigo, type_=Unicode()),
            bindparam("anexo", anexo, type_=Unicode()),
        ))
    return condiciones, parametros


def consulta_agregados(origen, filtros, por, *, ranking=None):
    if set(por) - set(DIMENSIONES) or len(set(por)) != len(por):
        raise ValueError("Las dimensiones deben ser válidas y únicas.")
    if ranking not in {None, "matricula", "retiro"} or (ranking and not por):
        raise ValueError("El ranking requiere una medida y dimensiones válidas.")
    conteo = "COUNT_BIG" if origen == "sql" else "COUNT"
    condiciones, parametros = _condiciones(filtros)
    medidas = []
    for medida in MEDIDAS_CSV:
        expresion = f"SUM({medida})"
        if medida in DISPONIBILIDAD:
            expresion = (
                f"CASE WHEN MIN(CASE WHEN {medida} IS NULL THEN 0 ELSE 1 END)=1 "
                f"THEN SUM(COALESCE({medida}, 0)) END"
            )
        medidas.append(f"{expresion} AS {medida}")
    # El código modular y el anexo conservan sus longitudes fijas en ambos orígenes.
    columnas = (*por, f"{conteo}(*) AS filas",
                f"{conteo}(DISTINCT CONCAT(cod_mod, anexo)) AS servicios", *medidas)
    consulta = f"SELECT {', '.join(columnas)}\nFROM {TABLAS[origen]}"
    if condiciones:
        consulta += f"\nWHERE {' AND '.join(condiciones)}"
    if por:
        columnas_grupo = ", ".join(por)
        consulta += f"\nGROUP BY {columnas_grupo}"
        orden = columnas_grupo
        if ranking == "matricula":
            orden = f"SUM(matricula) DESC, {columnas_grupo}"
        if ranking == "retiro":
            consulta += "\nHAVING SUM(matricula)>=10"
            orden = f"100.0*SUM(retirados)/NULLIF(SUM(matricula), 0) DESC, {columnas_grupo}"
        consulta += f"\nORDER BY {orden}"
    else:
        consulta += f"\nHAVING {conteo}(*)>0"
    if ranking:
        consulta += "\nOFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY" if origen == "sql" else "\nLIMIT 100"
    return text(consulta).bindparams(*parametros)


def consulta_opciones(origen, columnas):
    if not columnas or set(columnas) - set(DIMENSIONES):
        raise ValueError("Dimensiones de catálogo inválidas.")
    campos = ", ".join(columnas)
    return text(f"SELECT DISTINCT {campos} FROM {TABLAS[origen]} ORDER BY {campos}")


def consulta_servicios(origen, filtros, termino):
    condiciones, parametros = _condiciones(filtros)
    if len(termino) == 7 and termino.isascii() and termino.isdigit():
        condiciones.append("cod_mod=:codigo_buscado")
        parametros.append(bindparam("codigo_buscado", termino, type_=Unicode()))
    else:
        patron = termino.casefold().replace("~", "~~").replace("%", "~%").replace("_", "~_")
        if origen == "sql":
            patron = patron.replace("[", "~[")
        parametros.append(bindparam("patron", f"%{patron}%", type_=Unicode()))
        columnas = ("LOWER(nombre)", "cod_mod", "anexo")
        alternativas = " OR ".join(f"{c} LIKE :patron ESCAPE '~'" for c in columnas)
        condiciones.append(f"({alternativas})")
    prefijo = "TOP (60) " if origen == "sql" else ""
    sufijo = "" if origen == "sql" else "LIMIT 60"
    return text(f"""
        SELECT {prefijo}cod_mod, anexo, MIN(nombre) AS nombre
        FROM {TABLAS[origen]}
        WHERE {' AND '.join(condiciones)}
        GROUP BY cod_mod, anexo
        ORDER BY cod_mod, anexo
        {sufijo}
    """).bindparams(*parametros)


def consulta_distribucion(origen, filtros, medida):
    if medida not in {"aprobados", "retirados", "total_atraso"}:
        raise ValueError("Medida incompatible con la distribución por servicio.")
    condiciones, parametros = _condiciones(filtros)
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return text(f"""
        WITH servicios AS (
            SELECT SUM(matricula) AS matricula, SUM({medida}) AS medida
            FROM {TABLAS[origen]} {where}
            GROUP BY cod_mod, anexo
            HAVING SUM(matricula)>0
        ), tramos AS (
            SELECT CASE WHEN medida=0 THEN 0
                        WHEN 100.0*medida<matricula THEN 1
                        WHEN 100.0*medida<5*matricula THEN 2
                        WHEN 100.0*medida<10*matricula THEN 3
                        WHEN 100.0*medida<50*matricula THEN 4
                        WHEN 100.0*medida<90*matricula THEN 5 ELSE 6 END AS tramo,
                   CASE WHEN matricula<10 THEN 1 ELSE 0 END AS matricula_baja
            FROM servicios
        )
        SELECT tramo, matricula_baja, COUNT(*) AS servicios
        FROM tramos GROUP BY tramo, matricula_baja ORDER BY tramo, matricula_baja
    """).bindparams(*parametros)

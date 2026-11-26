"""Indicadores sobre agregados de matrícula y disponibilidad del periodo."""

from src.data.contrato import DISPONIBILIDAD


NUMERADORES = (
    "aprobados", "retirados", "total_atraso", "promocion_guiada", "desaprobados",
)


def tasa(numerador, matricula):
    if numerador is None or not matricula:
        return None
    return 100 * numerador / matricula


def aplicar_indicadores(filas, periodos, anios):
    resultado = []
    for original in filas:
        fila = original.copy()
        alcance = (fila["anio"],) if "anio" in fila else anios
        for medida, bandera in DISPONIBILIDAD.items():
            if not all(periodos[anio][bandera] for anio in alcance):
                fila[medida] = None
        for medida in NUMERADORES:
            fila[f"tasa_{medida}"] = tasa(fila[medida], fila["matricula"])
        resultado.append(fila)
    return resultado


def variaciones_anuales(filas):
    """Recibe un total por año para el mismo conjunto de filtros."""
    por_anio = {fila["anio"]: fila["matricula"] for fila in filas}
    if len(por_anio) != len(filas):
        raise ValueError("La variación requiere un total por año.")
    resultado = []
    for fila in sorted(filas, key=lambda fila: fila["anio"]):
        anterior = por_anio.get(fila["anio"] - 1)
        diferencia = None if anterior is None else fila["matricula"] - anterior
        resultado.append({
            **fila, "matricula_anterior": anterior, "variacion_pct": tasa(diferencia, anterior),
        })
    return resultado

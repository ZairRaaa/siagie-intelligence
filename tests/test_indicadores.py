import pytest
from sqlalchemy.dialects import mssql

from src.analytics.indicadores import tasa, variaciones_anuales
from src.data.consultas import consulta_agregados
from src.data.contrato import Filtros
from src.data.fuente_analitica import FuenteAnalitica


@pytest.fixture(scope="module")
def fuente():
    with FuenteAnalitica("csv") as origen:
        yield origen


def test_totales_y_tasa_ponderada(fuente):
    anual = fuente.agregados()
    total, = fuente.agregados(por=())
    assert [fila["matricula"] for fila in anual] == [8173597, 8274834, 8252287, 8153638]
    assert total["filas"] == 2205115
    assert total["matricula"] == 32854356
    assert total["servicios"] < sum(fila["servicios"] for fila in anual)
    assert total["tasa_aprobados"] == 100 * sum(fila["aprobados"] for fila in anual) / 32854356


def test_disponibilidad_por_anio_y_periodo(fuente):
    anual = fuente.agregados()
    total, = fuente.agregados(por=())
    assert [fila["promocion_guiada"] for fila in anual] == [376281, 232653, None, None]
    assert [fila["desaprobados"] for fila in anual] == [None, None, 250490, 241286]
    assert total["tasa_promocion_guiada"] is None
    assert total["tasa_desaprobados"] is None
    solo_una_etapa, = fuente.agregados(Filtros(anios=(2023, 2024)), por=())
    assert solo_una_etapa["desaprobados"] == 491776


def test_edad_desconocida_vacia_y_cero(fuente):
    desconocida, = fuente.agregados(Filtros(edades=(None,)), por=("edad",))
    cero, = fuente.agregados(Filtros(edades=(0,)), por=("edad",))
    assert desconocida["edad"] is None and desconocida["filas"] == 6
    assert cero["edad"] == 0 and cero["filas"] > 0
    assert fuente.agregados(Filtros(anios=()), por=()) == []
    assert fuente.agregados(Filtros(gestiones=()), por=("anio",)) == []


def test_servicio_con_ceros_y_codigo_inexistente(fuente):
    servicio, = fuente.agregados(Filtros(servicio=("0001506", "000")), por=())
    assert servicio["servicios"] == 1
    assert servicio["matricula"] > 0
    assert fuente.agregados(Filtros(servicio=("0000000", "999")), por=()) == []


def test_tasas_sin_denominador_y_serie_con_salto(fuente):
    assert tasa(0, 7) == 0
    assert tasa(1, 0) is None
    assert tasa(None, 10) is None
    variaciones = variaciones_anuales(fuente.agregados(Filtros(anios=(2021, 2023, 2024))))
    assert variaciones[1]["variacion_pct"] is None
    assert variaciones[2]["matricula_anterior"] == 8252287
    assert variaciones[2]["variacion_pct"] == pytest.approx(-1.1954146766)


def test_sql_parametrizado_y_columnas_controladas():
    valor = "gestión con ' comilla"
    consulta = consulta_agregados("sql", Filtros(gestiones=(valor,)), ("anio",))
    compilado = consulta.compile(dialect=mssql.dialect())
    assert valor not in str(compilado)
    assert compilado.params["gestion"] == (valor,)
    with pytest.raises(ValueError, match="dimensiones"):
        consulta_agregados("sql", Filtros(), ("campo_no_permitido",))

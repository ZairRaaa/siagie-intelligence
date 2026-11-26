import csv
from io import StringIO
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ui.componentes import csv_bytes


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def aplicacion():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not app.exception
    return app


def test_resumen_con_fuente_y_matricula_reales(aplicacion):
    app = aplicacion
    assert app.title[0].value == "Resumen ejecutivo"
    assert app.selectbox(key="origen").value == "csv"
    assert app.metric[0].value == "32\u202f854\u202f356"
    assert app.metric[1].value == "111\u202f049"
    assert len(app.get("plotly_chart")) == 2
    assert len(app.download_button) == 2


def test_cambio_de_anio_y_seleccion_vacia(aplicacion):
    app = aplicacion
    try:
        app.multiselect(key="anios").set_value([2024]).run()
        assert not app.exception
        assert app.metric[0].value == "8\u202f153\u202f638"
        assert any("-1,20 %" in caption.value for caption in app.caption)
        app.multiselect(key="anios").set_value([]).run()
        assert any("No hay registros" in mensaje.value for mensaje in app.info)
        assert not app.metric
    finally:
        app.multiselect(key="anios").set_value([2021, 2022, 2023, 2024]).run()


def test_trayectoria_con_desaprobacion_parcial(aplicacion):
    app = aplicacion
    app.radio(key="pagina").set_value("Matrícula y trayectoria").run()
    app.selectbox(key="situacion_final").set_value("desaprobados").run()
    assert not app.exception
    assert any("disponibilidad parcial" in mensaje.value for mensaje in app.info)
    assert app.multiselect(key="edades")
    assert len(app.download_button) == 2
    app.toggle(key="comparar_trayectoria").set_value(True).run()
    assert not app.exception and not app.error
    assert len(app.get("plotly_chart")) == 3


def test_servicios_busqueda_ranking_e_historial(aplicacion):
    app = aplicacion
    app.radio(key="pagina").set_value("Análisis de servicios").run()
    assert not app.exception
    assert not app.error
    assert len(app.dataframe[0].value) == 100
    assert app.dataframe[0].value["anio"].eq(2024).all()
    app.selectbox(key="servicios_orden").set_value("retiro").run()
    assert app.dataframe[0].value["matricula"].ge(10).all()
    assert app.dataframe[0].value["tasa_retirados"].is_monotonic_decreasing
    app.text_input(key="buscar_servicio").set_value("0001506").run()
    app.selectbox(key="servicio").set_value(("0001506", "000")).run()
    assert not app.exception
    assert app.dataframe[0].value["cod_mod"].eq("0001506").all()
    assert list(app.dataframe[0].value["anio"]) == [2021, 2022, 2023, 2024]


def test_pagina_metodologia(aplicacion):
    app = aplicacion
    app.radio(key="pagina").set_value("Datos y metodología").run()
    assert not app.exception
    assert app.title[0].value == "Datos y metodología"
    assert list(app.dataframe[0].value["Año"]) == [2021, 2022, 2023, 2024]


def test_csv_exportado_preserva_texto_y_disponibilidad():
    salida = csv_bytes([{
        "anio": 2024, "cod_mod": "0001506", "nombre": "=fórmula", "desaprobados": None,
    }], ("anio", "cod_mod", "nombre", "desaprobados"), "csv")
    fila, = csv.DictReader(StringIO(salida.decode("utf-8-sig")))
    assert fila == {
        "origen": "CSV SIAGIE verificados", "anio": "2024", "cod_mod": "0001506",
        "nombre": "'=fórmula", "desaprobados": "",
    }

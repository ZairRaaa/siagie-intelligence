import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from src.ai import analisis
from src.data.contrato import Filtros
from src.ui import asistente as interfaz


RESPUESTA = {
    "titulo": "Lectura del corte",
    "puntos": [
        {"texto": "La matrícula resume el alcance observado.", "evidencia": "matricula"},
        {"texto": "Los servicios se cuentan mediante su clave natural.", "evidencia": "servicios"},
    ],
    "alcance": "Corresponde a las matrículas registradas.",
}


def test_contexto_agregado_sin_identificadores_de_servicio():
    filtros = Filtros(anios=(2023, 2024), servicio=("0001506", "000"))
    total = {"matricula": 12, "servicios": 1, "tasa_aprobados": 95, "tasa_retirados": 0, "tasa_total_atraso": 0}
    anual = [{"anio": 2023, "matricula": 7, "variacion_pct": None},
             {"anio": 2024, "matricula": 5, "variacion_pct": -28.57, "nombre": "Nombre excluido"}]
    contexto = interfaz.datos_resumen(total, anual, filtros, "csv")
    serializado = json.dumps(contexto)
    assert contexto["un_servicio"] is True
    assert "0001506" not in serializado and "Nombre excluido" not in serializado
    assert "-2 matrículas" in contexto["hechos"]["cambio_entre_extremos"]


@pytest.mark.parametrize("campo,valor", [("evidencia", "desconocida"), ("texto", "Tasa de 101 %.")])
def test_rechaza_cifras_generadas_y_referencias_ajenas(campo, valor):
    salida = json.loads(json.dumps(RESPUESTA))
    salida["puntos"][0][campo] = valor
    with pytest.raises(analisis.ErrorAsistente):
        analisis.validar_respuesta(json.dumps(salida), {"matricula": "", "servicios": ""})


def test_responses_sin_almacenamiento_solicitado_y_sondeo_sin_datos(monkeypatch):
    solicitudes = []
    monkeypatch.setattr(analisis, "configuracion", lambda: ("clave_de_prueba", "modelo"))

    def crear(**parametros):
        solicitudes.append(parametros)
        return SimpleNamespace(status="completed", output_text=json.dumps(RESPUESTA), model="modelo")

    class Cliente:
        def __init__(self, **parametros):
            assert parametros["base_url"] == "https://api.openai.com/v1"
            self.responses = SimpleNamespace(create=crear)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(analisis, "OpenAI", Cliente)
    hechos = {"matricula": "12", "servicios": "1"}
    resultado, modelo = analisis.generar("explicar", {"hechos": hechos})
    assert resultado == RESPUESTA and modelo == "modelo"
    assert solicitudes[0]["store"] is False
    assert solicitudes[0]["text"]["format"]["strict"] is True
    assert "clave_de_prueba" not in solicitudes[0]["input"]
    analisis.comprobar_conexion()
    assert solicitudes[1]["input"] == "Reply with the word OK."


def test_cuota_produce_mensaje_sin_detalles_de_la_credencial():
    error = analisis._error_api(SimpleNamespace(status_code=429, code="insufficient_quota"))
    assert error.codigo == "cuota"
    assert "saldo" in str(error)


def test_dashboard_llama_solo_por_accion_e_invalida_el_corte(monkeypatch):
    monkeypatch.setattr(interfaz, "configuracion", lambda: ("clave_de_prueba", "modelo"))
    peticiones = []

    def generar(accion, contexto):
        peticiones.append((accion, contexto))
        return RESPUESTA, "modelo"

    monkeypatch.setattr(interfaz, "generar", generar)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=90).run()
    assert not app.exception and not peticiones
    boton = next(x for x in app.button if x.label == "Generar con GPT")
    boton.click().run()
    assert not app.exception and len(peticiones) == 1
    assert peticiones[0][1]["periodo"] == "2021–2024"
    assert any(x.label == "Descargar explicación" for x in app.download_button)
    app.multiselect(key="anios").set_value([2024]).run()
    assert not app.exception and len(peticiones) == 1
    assert not any(x.label == "Descargar explicación" for x in app.download_button)
    assert all("Comparar años" not in x.options for x in app.selectbox)

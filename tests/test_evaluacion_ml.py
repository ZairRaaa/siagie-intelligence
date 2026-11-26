import math
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scripts.entrenar_matricula import elegir_validacion, ejecutar, verificar
from src.ml.artefactos import leer_json
from src.ml.evaluacion import metricas, tamanos
from src.ml.modelos import candidatos
from src.ml.panel import PREDICTORES_BASE, PREDICTORES_TASAS
from src.ui import pagina_ml


def test_metricas_y_denominadores():
    resultado = metricas([10, 20], [12, 16])
    assert resultado == pytest.approx({"n": 2, "mae": 3, "rmse": math.sqrt(10), "r2": 0.6, "wape": 20})
    constantes = metricas([0], [2])
    assert constantes["r2"] is None and constantes["wape"] is None
    assert tamanos(pd.Series([1, 9, 10, 49, 50, 199, 200])).tolist() == [
        "1–9", "1–9", "10–49", "10–49", "50–199", "50–199", "200 o más",
    ]


def test_candidatos_solo_usen_atributos_del_anio_de_entrada():
    permitidas = set(PREDICTORES_BASE + PREDICTORES_TASAS)
    assert all(set(c.variables) <= permitidas for c in candidatos())


def test_seleccion_por_mae_de_validacion_y_desempate_con_persistencia():
    resultado = [
        {"modelo": "persistencia", "id": "persistencia", "mae": 3},
        {"modelo": "ridge", "id": "ridge_a", "mae": 3},
        {"modelo": "ridge", "id": "ridge_b", "mae": 4},
        {"modelo": "hgb", "id": "hgb", "mae": 5},
    ]
    assert elegir_validacion(resultado) == (
        {"persistencia": "persistencia", "ridge": "ridge_a", "hgb": "hgb"}, "persistencia",
    )


def test_verificacion_no_ajusta_y_deja_reservados_los_datos_de_prueba(monkeypatch):
    import scripts.entrenar_matricula as script

    monkeypatch.setattr(script, "parametros_protocolo", lambda *_: {"versiones": {"scikit_learn": "prueba"}})
    leidas, huellas = [], []
    monkeypatch.setattr(script, "leer_particion", lambda _, nombre: leidas.append(nombre) or [None])
    monkeypatch.setattr(script, "ruta_particion", lambda _, nombre: huellas.append(nombre))
    monkeypatch.setattr(script, "ajustar", lambda *_: pytest.fail("El preflight llamó al ajuste."))
    verificar({}, 2)
    assert leidas == ["entrenamiento", "validacion"]
    assert huellas == ["prueba"]


def test_congela_seleccion_antes_de_evaluar_y_reutiliza_ejecucion(tmp_path, monkeypatch):
    import scripts.entrenar_matricula as script

    seleccion = {"elegido": "ridge", "protocolo": {}}
    monkeypatch.setattr(script, "directorio_ejecucion", lambda _: tmp_path)
    monkeypatch.setattr(script, "parametros_protocolo", lambda *_: {})
    leidas = []
    monkeypatch.setattr(script, "leer_particion", lambda _, nombre: leidas.append(nombre))
    monkeypatch.setattr(script, "seleccionar", lambda *_: seleccion)

    def evaluar(*_):
        assert leer_json(tmp_path / "seleccion.json") == seleccion
        assert leidas == ["entrenamiento", "validacion"]
        (tmp_path / "resumen.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(script, "evaluar_final", evaluar)
    ejecutar({}, 2)
    ejecutar({}, 2)
    assert leidas == ["entrenamiento", "validacion"]


def test_dashboard_muestra_panel_pendiente_sin_metricas(tmp_path, monkeypatch):
    monkeypatch.setattr(pagina_ml, "directorio_ejecucion", lambda _: tmp_path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["pagina"] = "ML · Predicciones"
    app.run()
    assert not app.exception and not app.error and not app.metric
    assert "cuando finalice el entrenamiento local" in app.info[0].value
    assert app.dataframe[0].value["Pares"].tolist() == [103931, 103722, 103856]


def test_filtro_de_servicio_conserva_ceros():
    datos = pd.DataFrame({"nivel_t": ["B0", "B0", "F0"], "cod_mod": ["0001506"] * 3,
                          "anexo": ["000", "001", "002"]})
    assert pagina_ml._filtrar_servicios(datos, "B0", "1506-1").anexo.tolist() == ["001"]
    with pytest.raises(ValueError):
        pagina_ml._filtrar_servicios(datos, "F0", "código")


def test_publicacion_y_visualizacion_de_una_ejecucion_de_prueba(tmp_path, monkeypatch):
    import scripts.entrenar_matricula as script

    manifiesto = leer_json(pagina_ml.MANIFIESTO)
    pares = pd.DataFrame({
        "anio_t": [2023, 2023], "anio_t1": [2024, 2024],
        "cod_mod": ["0000001", "0000002"], "anexo": ["000", "001"],
        "nivel_t": ["B0", "F0"], "gestion_t": ["Privada", "Privada"],
        "matricula_t": [15, 27], "matricula_t1": [18, 25],
    })
    seleccion = {
        "elegido": "ridge",
        "finalistas": {"persistencia": "persistencia", "ridge": "ridge_base_1", "hgb": "hgb_base_15"},
        "validacion": [],
    }
    monkeypatch.setattr(script, "ajustar", lambda *_: SimpleNamespace())
    monkeypatch.setattr(script, "predecir", lambda candidato, _, datos:
                        datos.matricula_t.to_numpy() + int(candidato.modelo == "ridge"))
    monkeypatch.setattr(script, "leer_particion", lambda _, nombre: pares if nombre == "prueba" else None)
    script.evaluar_final(tmp_path, manifiesto, seleccion, pares, pares, perf_counter())
    monkeypatch.setattr(pagina_ml, "directorio_ejecucion", lambda _: tmp_path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["pagina"] = "ML · Predicciones"
    app.run()
    assert not app.exception and not app.error
    assert len(app.metric) == 3 and len(app.get("plotly_chart")) == 2
    app.text_input(key="ml_servicio").set_value("1-0").run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "2,50"
    assert app.dataframe[3].value["cod_mod"].tolist() == ["0000001"]

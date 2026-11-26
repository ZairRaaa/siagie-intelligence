import pandas as pd
import pytest

from src.ml.panel import (
    COLUMNAS, OBJETIVO, PREDICTORES_BASE, PREDICTORES_TASAS, TIPOS, construir_pares,
    validar_panel,
)


@pytest.fixture
def panel():
    return pd.DataFrame([
        (2021, "0000001", "000", "B0", "Privada", 4, 20, 18, 1, 2),
        (2021, "0000002", "000", "B0", "Privada", 2, 8, 8, 0, 0),
        (2022, "0000001", "000", "F0", "Pública", 5, 35, 34, 0, 5),
        (2022, "0000001", "001", "F0", "Privada", 6, 50, 48, 1, 2),
        (2023, "0000002", "000", "B0", "Privada", 2, 10, 9, 1, 0),
        (2024, "0000001", "000", "F0", "Pública", 5, 36, 34, 1, 1),
    ], columns=COLUMNAS).astype(TIPOS)


def test_pares_exactos_y_atributos_del_anio_de_entrada(panel):
    validar_panel(panel)
    pares, cobertura = construir_pares(panel, 2021)
    assert pares[["cod_mod", "anexo"]].values.tolist() == [["0000001", "000"]]
    assert pares[OBJETIVO].tolist() == [35]
    assert pares[PREDICTORES_BASE].values.tolist() == [[20, "B0", "Privada"]]
    assert pares[PREDICTORES_TASAS].values.tolist() == [[90.0, 5.0, 10.0]]
    assert len(pares.columns) == 11
    assert (cobertura["sin_etiqueta"], cobertura["sin_antecedente_inmediato"]) == (1, 1)
    assert (cobertura["cambio_nivel"], cobertura["cambio_gestion"]) == (1, 1)


def test_ausencia_al_anio_siguiente_no_se_rellena(panel):
    pares, cobertura = construir_pares(panel, 2022)
    assert pares.empty
    assert cobertura["sin_etiqueta"] == 2
    assert cobertura["sin_antecedente_inmediato"] == 1


def test_panel_rechaza_claves_duplicadas(panel):
    duplicado = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="mismo servicio y año"):
        validar_panel(duplicado)


def test_panel_rechaza_un_conteo_mayor_a_matricula(panel):
    panel.loc[0, "retirados"] = 21
    with pytest.raises(ValueError, match="supera su matrícula"):
        validar_panel(panel)

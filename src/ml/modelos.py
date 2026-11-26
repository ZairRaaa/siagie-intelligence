"""Candidatos para selección temporal con preprocesamiento en el pipeline."""

from dataclasses import dataclass
from itertools import product

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.ml.panel import PREDICTORES_BASE, PREDICTORES_TASAS


SEMILLA = 42
CATEGORICAS = ("nivel_t", "gestion_t")


@dataclass(frozen=True)
class Candidato:
    id: str
    modelo: str
    variables: tuple[str, ...]
    parametros: dict


def candidatos():
    base = tuple(PREDICTORES_BASE)
    tasas = base + tuple(PREDICTORES_TASAS)
    opciones = [Candidato("persistencia", "persistencia", ("matricula_t",), {})]
    for nombre, variables in (("base", base), ("tasas", tasas)):
        opciones.extend(
            Candidato(f"ridge_{nombre}_{alpha:g}", "ridge", variables, {"alpha": alpha, "solver": "lsqr"})
            for alpha in (1.0, 10.0)
        )
        opciones.extend(
            Candidato(f"hgb_{nombre}_{hojas}", "hgb", variables, {
                "max_iter": 100, "max_leaf_nodes": hojas, "min_samples_leaf": 30,
                "learning_rate": 0.1, "early_stopping": False, "random_state": SEMILLA,
            })
            for hojas in (15, 31)
        )
    return opciones


def construir_modelo(candidato):
    if candidato.modelo == "persistencia":
        return None
    numericas = [nombre for nombre in candidato.variables if nombre not in CATEGORICAS]
    categ = [nombre for nombre in CATEGORICAS if nombre in candidato.variables]
    pasos_numericos = [("mediana", SimpleImputer(strategy="median"))]
    if candidato.modelo == "ridge":
        pasos_numericos.append(("escala", StandardScaler()))
    preprocesador = ColumnTransformer([
        ("numericas", Pipeline(pasos_numericos), numericas),
        ("categoricas", Pipeline([
            ("imputar", SimpleImputer(strategy="most_frequent")),
            ("codificar", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), categ),
    ])
    estimador = {"ridge": Ridge, "hgb": HistGradientBoostingRegressor}[candidato.modelo]
    return Pipeline([("preparar", preprocesador), ("modelo", estimador(**candidato.parametros))])

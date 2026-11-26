"""Recalcula controles agregados sobre las exportaciones originales del SIAGIE."""
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FUENTES = ROOT / "contexto"
SERVICIO = ["cod_mod", "anexo"]
GRANO = SERVICIO + ["id_nivel", "Edad", "TipoDiscaIntegrada"]
DIMENSIONES = set(GRANO + ["Nombre", "gestion", "dsc_nivel"])


def auditar(fuente):
    ruta = FUENTES / fuente["archivo"]
    with ruta.open("rb") as archivo:
        huella = hashlib.file_digest(archivo, "sha256").hexdigest()
    datos = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    medidas = datos.columns.difference(DIMENSIONES)
    numeros = datos[medidas].apply(pd.to_numeric, errors="raise")
    total = numeros["TotalEstudiantes"]
    grupos = datos.groupby(SERVICIO)
    panel = grupos[["id_nivel", "gestion"]].first()
    panel["matricula"] = total.groupby([datos[c] for c in SERVICIO]).sum()
    categorias = {
        "sexo": ["Mujer", "Hombre"],
        "nacionalidad": ["Venezolanos", "Peruanos", "Extranjeros"],
        "documento": ["DNI_validado", "DNI_SinValidar", "No_DNI"],
        "situacion": ["Aprobado", "Retirado", "Fallecido", "RequiereRecuperacion",
                      "Matriculado", "PostergaEvaluacion",
                      "PromocionGuiada" if "PromocionGuiada" in numeros else "Desaprobado"],
    }
    vacios = datos.eq("").sum()
    return panel, {
        "archivo": ruta.name, "sha256": huella, "coincide_sha256": huella == fuente["sha256"],
        "coincide_encabezado": datos.columns.tolist() == fuente["columnas"],
        "filas": len(datos), "matricula": int(total.sum()), "servicios": len(panel),
        "duplicados_grano": int(datos.duplicated(GRANO).sum()),
        "vacios": vacios[vacios.gt(0)].to_dict(),
        "medidas_negativas": int(numeros.lt(0).sum().sum()),
        "medidas_sin_valor": int(numeros.isna().sum().sum()),
        "medidas_sobre_total": int(numeros.gt(total, axis=0).sum().sum()),
        "descuadres": {c: int(numeros[cols].sum(axis=1).ne(total).sum())
                       for c, cols in categorias.items()},
        "conflictos_intra_anuales": grupos[["Nombre", "gestion", "id_nivel"]].nunique().gt(1).sum().to_dict(),
        "servicios_sin_matricula": int(panel.matricula.eq(0).sum()),
        "servicios_menos_10": int(panel.matricula.lt(10).sum()),
    }


def main():
    manifiesto = json.loads((FUENTES / "resultados/manifiesto_fuentes.json").read_text("utf-8-sig"))
    anuales, pares = {}, {}
    anterior = None
    for fuente in sorted(manifiesto["fuentes"], key=lambda f: f["anio"]):
        anio = fuente["anio"]
        panel, anuales[anio] = auditar(fuente)
        if anterior is not None and ultimo == anio - 1:
            comunes = anterior.index.intersection(panel.index)
            pares[f"{ultimo}-{anio}"] = {
                "pares": len(comunes), "sin_etiqueta": len(anterior) - len(comunes),
                "sin_antecedente": len(panel) - len(comunes),
                "cobertura_origen_pct": round(100 * len(comunes) / len(anterior), 3),
                "cambio_nivel": int(anterior.loc[comunes, "id_nivel"].ne(panel.loc[comunes, "id_nivel"]).sum()),
                "cambio_gestion": int(anterior.loc[comunes, "gestion"].ne(panel.loc[comunes, "gestion"]).sum()),
            }
        anterior, ultimo = panel, anio
        print(anio, anuales[anio]["filas"], flush=True)
    salida = ROOT / "results" / "diagnostico_fuentes.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps({"anuales": anuales, "pares": pares}, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    main()

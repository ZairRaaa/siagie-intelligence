"""Resultados de la prueba histórica generados por una ejecución local."""

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ml.artefactos import MANIFIESTO, METRICAS, MODELOS, directorio_ejecucion, leer_json, sha256_archivo
from src.ml.evaluacion import TAMANOS
from src.ui.asistente import asistente, datos_ml
from src.ui.componentes import AZUL, NIVELES, VERDE, grafico, numero, porcentaje


ETIQUETAS = {
    "modelo": "Modelo", "n": "Pares", "mae": "MAE", "rmse": "RMSE", "r2": "R²", "wape": "WAPE (%)",
    "real": "Matrícula observada", "predicho": "Matrícula estimada",
    "error": "Error (estimado − observado)", "nivel_t": "Nivel de entrada", "tamano": "Tamaño de entrada",
}
COLUMNAS_DESCARGA = (
    "modelo", "cod_mod", "anexo", "anio_t", "anio_t1", "nivel_t", "gestion_t",
    "matricula_t", "real", "predicho", "error",
)


@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def _cargar_resultados(carpeta, firmas):
    archivos = {}
    for nombre, huella, _ in firmas:
        ruta = Path(carpeta) / nombre
        if sha256_archivo(ruta) != huella:
            raise ValueError(f"La huella de {nombre} difiere de la ejecución registrada.")
        archivos[nombre] = pd.read_parquet(ruta) if nombre.endswith(".parquet") else pd.read_csv(ruta)
    return archivos["predicciones.parquet"], archivos["metricas_segmentos.csv"]


def _protocolo(manifiesto):
    with st.expander("Protocolo y cobertura", expanded=True):
        datos = [{
            "Partición": etiqueta, "Entrada": manifiesto["particiones"][nombre]["anio_t"],
            "Objetivo": manifiesto["particiones"][nombre]["anio_t1"],
            "Pares": manifiesto["particiones"][nombre]["pares"],
            "Cobertura": porcentaje(manifiesto["particiones"][nombre]["cobertura_origen_pct"]),
        } for nombre, etiqueta in (
            ("entrenamiento", "Entrenamiento"), ("validacion", "Validación"), ("prueba", "Prueba reservada"),
        )]
        st.dataframe(pd.DataFrame(datos), hide_index=True, width="stretch")
        st.caption("La cobertura corresponde a servicios de entrada con matrícula observada al año siguiente.")
        st.write("La persistencia usa la última matrícula observada. Ridge y HistGradientBoosting se seleccionan por MAE de validación.")


def _filtrar_servicios(datos, nivel, termino):
    if nivel is not None:
        datos = datos[datos.nivel_t.eq(nivel)]
    if termino:
        partes = re.fullmatch(r"([0-9]{1,7})(?:[- /]([0-9]{1,3}))?", termino)
        if partes is None:
            raise ValueError("Usa un código modular y, si corresponde, un anexo separado por guion.")
        codigo, anexo = partes.groups()
        datos = datos[datos.cod_mod.eq(codigo.zfill(7))]
        if anexo:
            datos = datos[datos.anexo.eq(anexo.zfill(3))]
    return datos


def _mostrar_corte(datos, modelo):
    st.subheader("Predicciones por servicio")
    cuenta = len(datos)
    if cuenta == 0:
        st.info("No hay servicios elegibles para este corte.")
        return
    muestra = datos.sample(4000, random_state=42) if cuenta > 4000 else datos
    unidad = "par" if cuenta == 1 else "pares"
    st.caption(f"{numero(cuenta)} {unidad} en el corte. Los gráficos muestran {numero(len(muestra))}.")
    real_vs, residuos = st.columns((1.2, 1))
    with real_vs, st.container(border=True):
        st.subheader("Observado frente a estimado")
        fig = px.scatter(muestra, x="real", y="predicho", labels=ETIQUETAS,
                         hover_data=["cod_mod", "anexo"], opacity=0.55, color_discrete_sequence=[VERDE])
        limite = max(float(muestra.real.max()), float(muestra.predicho.max()))
        fig.add_shape(type="line", x0=0, y0=0, x1=limite, y1=limite,
                      line={"color": "#526887", "dash": "dash"})
        grafico(fig, "ml_real_estimado", altura=370)
    with residuos, st.container(border=True):
        st.subheader("Distribución de errores")
        fig = px.histogram(muestra, x="error", nbins=50, labels=ETIQUETAS, color_discrete_sequence=[AZUL])
        fig.update_yaxes(title="Servicios")
        fig.add_vline(x=0, line_dash="dash", line_color="#526887")
        grafico(fig, "ml_residuos", altura=370)
    tabla = datos[list(COLUMNAS_DESCARGA)].copy()
    tabla["modelo"] = MODELOS[modelo]
    st.dataframe(tabla.head(100).rename(columns=ETIQUETAS), hide_index=True, width="stretch")
    st.caption("La tabla muestra hasta 100 registros. La descarga contiene el corte completo.")
    st.download_button(
        "Descargar predicciones CSV",
        data=lambda: tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"siagie_prueba_2024_{modelo}.csv", mime="text/csv", on_click="ignore",
    )


def _mostrar_ejecucion(resumen, predicciones, segmentos):
    elegido = resumen["elegido"]
    pruebas = {fila["modelo"]: fila for fila in resumen["metricas_prueba"]}
    evaluacion = pruebas[elegido]
    diferencia = pruebas["persistencia"]["mae"] - evaluacion["mae"]
    st.subheader("Evaluación global")
    st.caption(f"Selección por validación · {MODELOS[elegido]} · {numero(evaluacion['n'])} pares en la prueba")
    mae, rmse, r2 = st.columns(3)
    mae.metric("MAE de la selección", numero(evaluacion["mae"], 2), border=True)
    rmse.metric("RMSE de la selección", numero(evaluacion["rmse"], 2), border=True)
    r2.metric("R² de la selección", numero(evaluacion["r2"], 3), border=True)
    if elegido == "persistencia":
        menor_en_prueba = all(evaluacion["mae"] < fila["mae"] for clave, fila in pruebas.items() if clave != elegido)
        resultado = " También obtuvo el menor MAE en la prueba histórica." if menor_en_prueba else ""
        st.info(f"La persistencia fue seleccionada por MAE de validación.{resultado}")
    elif diferencia > 0:
        st.info(f"La selección redujo el MAE de prueba en {numero(diferencia, 3)} matrículas frente a persistencia.")
    else:
        st.info("La selección de validación no redujo el MAE de prueba frente a persistencia.")
    comparacion = pd.DataFrame(resumen["metricas_prueba"], columns=["modelo", *METRICAS])
    comparacion["modelo"] = comparacion.modelo.map(MODELOS)
    config = {
        campo: st.column_config.NumberColumn(ETIQUETAS[campo], format=formato)
        for campo, formato in (("n", "%d"), ("mae", "%.2f"), ("rmse", "%.2f"),
                                ("r2", "%.4f"), ("wape", "%.2f %%"))
    }
    config["modelo"] = "Modelo"
    st.dataframe(comparacion, column_config=config, hide_index=True, width="stretch")
    asistente(datos_ml(resumen), ("ml",), "gpt_ml")

    st.subheader("Errores por segmento")
    modelo = st.selectbox("Modelo para el detalle", tuple(MODELOS), index=list(MODELOS).index(elegido),
                          format_func=MODELOS.get, key="ml_modelo")
    cortes = segmentos[segmentos.modelo.eq(modelo)]
    nivel, tamano = st.columns(2)
    for columna, dimension, etiqueta in ((nivel, "nivel_t", "Nivel educativo"), (tamano, "tamano", "Tamaño")):
        with columna:
            st.markdown(f"**{etiqueta}**")
            datos = cortes.loc[cortes.dimension.eq(dimension), ["segmento", *METRICAS]].copy()
            if dimension == "nivel_t":
                datos["segmento"] = datos.segmento.map(lambda item: NIVELES.get(item, item))
            else:
                datos = datos.set_index("segmento").reindex(TAMANOS).dropna(subset=["n"]).reset_index()
            st.dataframe(datos.rename(columns={**ETIQUETAS, "segmento": etiqueta}),
                         hide_index=True, width="stretch")

    fuente = predicciones.loc[predicciones.modelo.eq(modelo)]
    izquierda, derecha = st.columns(2)
    niveles = sorted(fuente.nivel_t.unique())
    filtro_nivel = izquierda.selectbox(
        "Nivel para el corte", niveles, index=None, placeholder="Todos los niveles",
        format_func=lambda item: NIVELES.get(item, item), key="ml_nivel",
    )
    codigo = derecha.text_input("Código modular o código-anexo", key="ml_servicio", max_chars=11).strip()
    try:
        datos = _filtrar_servicios(fuente, filtro_nivel, codigo)
    except ValueError as error:
        st.warning(str(error))
        return
    _mostrar_corte(datos, modelo)


def predicciones():
    st.title("ML · Predicciones")
    st.caption("Matrícula del siguiente año por servicio educativo · evaluación histórica 2023 → 2024")
    try:
        manifiesto = leer_json(MANIFIESTO)
        carpeta = directorio_ejecucion(manifiesto)
        ruta_resultados = carpeta / "resumen.json"
        if not ruta_resultados.is_file():
            st.info("El panel está preparado. La evaluación se mostrará cuando finalice el entrenamiento local.")
            _protocolo(manifiesto)
            return
        resumen = leer_json(ruta_resultados)
        if resumen["sha256_panel"] != manifiesto["sha256_panel_canonico"]:
            raise ValueError("La ejecución corresponde a otra versión del panel.")
        firmas = tuple(
            (nombre, resumen["artefactos_sha256"][nombre], (carpeta / nombre).stat().st_mtime_ns)
            for nombre in ("predicciones.parquet", "metricas_segmentos.csv")
        )
        datos, segmentos = _cargar_resultados(str(carpeta), firmas)
        st.caption(f"Origen · {resumen['origen']}")
        st.caption(f"Tiempo de ejecución registrado · {numero(resumen['segundos_ejecucion'], 2)} s")
        _mostrar_ejecucion(resumen, datos, segmentos)
        _protocolo(manifiesto)
    except (OSError, KeyError, ValueError):
        st.error("No se pudieron leer los artefactos del panel o de la evaluación local.")

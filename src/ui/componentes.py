"""Presentación de cifras, gráficos y descargas del dashboard."""

import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ESTILO = (Path(__file__).with_name("estilo.css")).read_text(encoding="utf-8")
ORIGENES = {"csv": "CSV SIAGIE verificados", "sql": "DW_SIAGIE · SQL Server"}
VERDE, AZUL, DORADO = "#087B68", "#386A9B", "#AA641A"
NIVELES = {
    "A1": "Inicial · Cuna", "A2": "Inicial · Jardín", "A3": "Inicial · Cuna-Jardín",
    "A5": "Inicial no escolarizado", "B0": "Primaria", "F0": "Secundaria",
}
ETIQUETAS = {
    "anio": "Año", "nivel": "Nivel", "nivel_nombre": "Nivel educativo", "gestion": "Gestión",
    "cod_mod": "Código modular", "anexo": "Anexo", "nombre": "Servicio educativo",
    "matricula": "Matrícula", "servicios": "Servicios", "filas": "Filas agrupadas",
    "aprobados": "Aprobados", "retirados": "Retirados", "total_atraso": "Atraso",
    "promocion_guiada": "Promoción guiada", "desaprobados": "Desaprobados",
    "fallecidos": "Fallecidos", "requieren_recuperacion": "Requieren recuperación",
    "cantidad_situacion_matriculado": "Situación «Matriculado»",
    "postergan_evaluacion": "Postergan evaluación", "variacion_pct": "Variación (%)",
    "tasa_aprobados": "Aprobación (%)", "tasa_retirados": "Retiro (%)",
    "tasa_total_atraso": "Atraso (%)", "tasa_promocion_guiada": "Promoción guiada (%)",
    "tasa_desaprobados": "Desaprobación (%)", "rango_edad": "Rango de edad",
    "tipo_discapacidad": "Tipo registrado", "cantidad_discapacidad": "Discapacidad registrada",
    "mujeres": "Mujeres", "hombres": "Hombres", "venezolanos": "Venezolanos",
    "peruanos": "Peruanos", "otros_extranjeros": "Otros extranjeros",
}
GESTIONES = {
    "Pública de gestión directa": VERDE,
    "Pública de gestión privada": AZUL,
    "Privada": DORADO,
}


def numero(valor, decimales=0):
    if valor is None or pd.isna(valor):
        return "N/D"
    return f"{valor:,.{decimales}f}".replace(",", "\u202f").replace(".", ",")


def porcentaje(valor, signo=False):
    if valor is None or pd.isna(valor):
        return "N/D"
    prefijo = "+" if signo and valor > 0 else ""
    return f"{prefijo}{numero(valor, 2)} %"


def periodo_texto(anios):
    if not anios:
        return "Sin años seleccionados"
    if len(anios) > 1 and tuple(range(min(anios), max(anios) + 1)) == tuple(anios):
        return f"{min(anios)}–{max(anios)}"
    return ", ".join(map(str, anios))


def encabezado(titulo, descripcion, origen, anios):
    st.title(titulo)
    st.caption(descripcion)
    st.html(f'<div class="siagie-origen">Perú · {periodo_texto(anios)} · {ORIGENES[origen]}</div>')


def grafico(figura, clave, altura=320):
    figura.update_layout(
        template="plotly_white", height=altura, separators=",.", font={"color": "#203952", "size": 13},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 18, "t": 18, "b": 10},
        legend={"orientation": "h", "y": -0.18, "x": 0, "title": {"text": ""}},
        hoverlabel={"bgcolor": "#17354C", "font_color": "#fff"},
    )
    figura.update_yaxes(gridcolor="#DFE7EF", zerolinecolor="#D5E0EB", automargin=True)
    figura.update_xaxes(gridcolor="#DFE7EF", zerolinecolor="#D5E0EB", automargin=True)
    st.plotly_chart(
        figura, key=clave, width="stretch", theme=None, config={"displayModeBar": False},
    )


def evolucion(filas, clave):
    por_anio = {fila["anio"]: fila for fila in filas}
    anios = list(range(min(por_anio), max(por_anio) + 1))
    matricula = [por_anio.get(anio, {}).get("matricula") for anio in anios]
    cambios = [porcentaje(por_anio.get(anio, {}).get("variacion_pct"), signo=True) for anio in anios]
    figura = go.Figure(go.Scatter(
        x=anios, y=matricula, mode="lines+markers", connectgaps=False, customdata=cambios,
        line={"color": VERDE, "width": 3}, marker={"size": 9, "color": VERDE},
        hovertemplate="%{x}<br>Matrícula: %{y:,.0f}<br>Variación: %{customdata}<extra></extra>",
    ))
    figura.update_xaxes(tickmode="array", tickvals=anios, showgrid=False)
    figura.update_yaxes(title="Matrículas", separatethousands=True)
    grafico(figura, clave)


def niveles_gestion(filas, clave):
    datos = pd.DataFrame(filas)
    etiquetas = {**ETIQUETAS, "nivel_nombre": "Nivel"}
    figura = px.bar(
        datos.groupby(["nivel_nombre", "gestion"], as_index=False)["matricula"].sum(),
        x="matricula", y="nivel_nombre", color="gestion", orientation="h", barmode="stack",
        labels=etiquetas, color_discrete_map=GESTIONES, hover_data={"matricula": ":,.0f"},
    )
    figura.update_yaxes(title=None, categoryorder="total ascending", showgrid=False)
    figura.update_xaxes(separatethousands=True)
    grafico(figura, clave, altura=360)


def tabla(filas, columnas, clave, *, altura="auto"):
    config = {}
    for campo in columnas:
        titulo = ETIQUETAS.get(campo, campo)
        if campo.startswith("tasa_") or campo == "variacion_pct":
            config[campo] = st.column_config.NumberColumn(titulo, format="%.2f %%")
        elif campo == "anio":
            config[campo] = st.column_config.NumberColumn(titulo, format="%d")
        else:
            config[campo] = titulo
    st.dataframe(
        pd.DataFrame(filas, columns=columnas), hide_index=True, column_config=config,
        key=clave, height=altura, width="stretch",
    )


def csv_bytes(filas, columnas, origen):
    salida = StringIO(newline="")
    escritor = csv.writer(salida)
    escritor.writerow(["origen", *columnas])
    for fila in filas:
        valores = [fila[campo] for campo in columnas]
        seguros = [
            "'" + valor if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@"))
            else valor for valor in valores
        ]
        escritor.writerow([ORIGENES[origen], *seguros])
    return salida.getvalue().encode("utf-8-sig")


def descargar(filas, columnas, origen, clave):
    st.download_button(
        "Descargar CSV", csv_bytes(filas, columnas, origen), f"siagie_{clave}_{origen}.csv",
        mime="text/csv", key=f"descarga_{clave}", on_click="ignore",
    )

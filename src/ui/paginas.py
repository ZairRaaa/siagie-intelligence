"""Páginas descriptivas del observatorio SIAGIE."""

from dataclasses import replace

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.indicadores import variaciones_anuales
from src.ui.asistente import asistente, datos_resumen
from src.ui.componentes import (
    AZUL, DORADO, ETIQUETAS, GESTIONES, VERDE, descargar, encabezado, evolucion, grafico,
    niveles_gestion, numero, porcentaje, tabla,
)


ANUAL = ("anio", "matricula", "servicios", "variacion_pct", "tasa_aprobados",
         "tasa_retirados", "tasa_total_atraso")
SITUACIONES = (
    "aprobados", "retirados", "desaprobados", "promocion_guiada", "requieren_recuperacion",
    "cantidad_situacion_matriculado", "fallecidos", "postergan_evaluacion",
)
NIVEL_GESTION = ("anio", "nivel", "nivel_nombre", "gestion", "matricula", "servicios",
                 "tasa_aprobados", "tasa_retirados", "tasa_total_atraso")
SIN_RESULTADOS = "No hay registros para los filtros seleccionados."


def _totales_anuales(fuente, filtros):
    # Consultar el año precedente incluso si queda fuera del periodo mostrado.
    disponibles = {fila["anio"] for fila in fuente.periodos()}
    anios = set(filtros.anios)
    alcance = anios | {anio - 1 for anio in anios if anio - 1 in disponibles}
    serie = fuente.agregados(replace(filtros, anios=tuple(sorted(alcance))))
    return [fila for fila in variaciones_anuales(serie) if fila["anio"] in anios]


def resumen(fuente, filtros):
    encabezado("Resumen ejecutivo", "Matrícula registrada y trayectoria en los servicios educativos.",
               fuente.origen, filtros.anios)
    with st.spinner("Consultando indicadores…"):
        totales = fuente.agregados(filtros, por=())
        if not totales:
            st.info(SIN_RESULTADOS)
            return
        anual = _totales_anuales(fuente, filtros)
        niveles = fuente.agregados(filtros, por=("anio", "nivel", "nivel_nombre", "gestion"))
    total = totales[0]
    tarjetas = st.columns((1.25, 1.15, 1, 1, 1))
    for columna, etiqueta, valor, ayuda in zip(tarjetas, (
        "Matrícula registrada", "Servicios", "Aprobación", "Retiro", "Atraso",
    ), (
        numero(total["matricula"]), numero(total["servicios"]), porcentaje(total["tasa_aprobados"]),
        porcentaje(total["tasa_retirados"]), porcentaje(total["tasa_total_atraso"]),
    ), (
        "Matrículas por año lectivo dentro de la selección.",
        "Códigos modulares y anexos distintos dentro de la selección.",
        "Aprobados sobre matrícula.", "Retirados sobre matrícula.", "Atraso sobre matrícula.",
    ), strict=True):
        columna.metric(etiqueta, valor, border=True, help=ayuda)
    izquierda, derecha = st.columns((1.2, 1))
    with izquierda, st.container(border=True, key="panel_evolucion"):
        st.subheader("Evolución de la matrícula")
        ultima = anual[-1]
        st.caption(f"Variación interanual en {ultima['anio']} · "
                   f"{porcentaje(ultima['variacion_pct'], signo=True)}")
        evolucion(anual, "resumen_evolucion")
    with derecha, st.container(border=True, key="panel_niveles"):
        st.subheader("Matrícula por nivel y gestión")
        niveles_gestion(niveles, "resumen_niveles")
    acciones = ("explicar", "comparar", "exponer") if len(anual) >= 2 else ("explicar", "exponer")
    asistente(datos_resumen(total, anual, filtros, fuente.origen), acciones, "gpt_resumen")
    with st.expander("Ver y exportar los datos"):
        anual_tab, niveles_tab = st.tabs(("Evolución anual", "Nivel y gestión"))
        with anual_tab:
            tabla(anual, ANUAL, "resumen_anual_tabla")
            descargar(anual, ANUAL, fuente.origen, "resumen_anual")
        with niveles_tab:
            tabla(niveles, NIVEL_GESTION, "resumen_niveles_tabla")
            descargar(niveles, NIVEL_GESTION, fuente.origen, "nivel_gestion")


def _caracteristica(fuente, filtros, anual):
    caracteristica = st.selectbox(
        "Característica", ("Rango de edad", "Sexo", "Nacionalidad", "Discapacidad registrada"),
        key="caracteristica",
    )
    if caracteristica in {"Rango de edad", "Discapacidad registrada"}:
        edad = caracteristica == "Rango de edad"
        dimension = "rango_edad" if edad else "tipo_discapacidad"
        medida = "matricula" if edad else "cantidad_discapacidad"
        filas = fuente.agregados(filtros, por=("anio", dimension))
        datos = pd.DataFrame(filas)
        total = datos.groupby(dimension, as_index=False)[medida].sum()
        if not edad:
            total = total[total[medida] > 0]
        if not total.empty:
            figura = px.bar(total, x=medida, y=dimension, orientation="h", labels=ETIQUETAS,
                            color_discrete_sequence=[AZUL], hover_data={medida: ":,.0f"})
            figura.update_yaxes(title=None, categoryorder="total ascending")
            grafico(figura, "caracteristicas_grafico", altura=370)
        else:
            st.info("El corte no contiene matrículas con discapacidad registrada.")
        columnas = ("anio", dimension, "matricula") if edad else ("anio", dimension, "matricula", medida)
    else:
        campos = ("mujeres", "hombres") if caracteristica == "Sexo" else (
            "peruanos", "venezolanos", "otros_extranjeros",
        )
        filas = anual
        columnas = ("anio", *campos)
        datos = pd.DataFrame(filas, columns=columnas)
        largo = datos.melt(id_vars="anio", var_name="categoría", value_name="matricula")
        largo["categoría"] = largo["categoría"].map(ETIQUETAS)
        figura = px.bar(
            largo, x="anio", y="matricula", color="categoría", labels=ETIQUETAS,
            color_discrete_sequence=[AZUL, VERDE, DORADO], hover_data={"matricula": ":,.0f"},
        )
        figura.update_xaxes(type="category")
        grafico(figura, "caracteristicas_grafico", altura=370)
    tabla(filas, columnas, "caracteristicas_tabla")
    descargar(filas, columnas, fuente.origen, "caracteristicas")


def trayectoria(fuente, filtros):
    encabezado("Matrícula y trayectoria", "Situación final y características registradas de la matrícula.",
               fuente.origen, filtros.anios)
    with st.spinner("Consultando trayectoria…"):
        anual = fuente.agregados(filtros)
    if not anual:
        st.info(SIN_RESULTADOS)
        return
    situacion, caracteristicas = st.tabs(("Situación final", "Características de la matrícula"))
    with situacion:
        st.subheader("Situaciones finales por año")
        medida = st.selectbox("Situación final", SITUACIONES, index=1, format_func=ETIQUETAS.get,
                              key="situacion_final")
        datos = pd.DataFrame(anual)
        disponibles = datos[datos[medida].notna()]
        if len(disponibles) < len(datos):
            st.info("La categoría seleccionada tiene disponibilidad parcial o nula en este periodo.")
        if not disponibles.empty:
            figura = px.bar(
                disponibles, x="anio", y=medida, labels=ETIQUETAS, color_discrete_sequence=[VERDE],
                hover_data={"matricula": ":,.0f", medida: ":,.0f"},
            )
            figura.update_xaxes(type="category")
            grafico(figura, "situaciones_grafico")
        st.caption("N/D identifica una categoría que no se publicó para ese año.")
        columnas = ("anio", "matricula", *SITUACIONES, "tasa_aprobados", "tasa_retirados")
        tabla(anual, columnas, "situaciones_tabla")
        descargar(anual, columnas, fuente.origen, "situaciones_finales")
        if st.toggle("Comparar tasas por nivel y gestión", key="comparar_trayectoria"):
            tasa = st.selectbox("Indicador de comparación",
                                ("tasa_retirados", "tasa_aprobados", "tasa_total_atraso"),
                                format_func=ETIQUETAS.get, key="tasa_trayectoria")
            anio = st.selectbox("Año para comparar", tuple(reversed(filtros.anios)), key="anio_trayectoria")
            corte = fuente.agregados(
                replace(filtros, anios=(anio,)), por=("anio", "nivel", "nivel_nombre", "gestion"),
            )
            if corte:
                figura = px.bar(
                    pd.DataFrame(corte), x=tasa, y="nivel_nombre", color="gestion", orientation="h",
                    barmode="group", labels=ETIQUETAS, color_discrete_map=GESTIONES,
                    hover_data={"matricula": ":,.0f", tasa: ":.2f"},
                )
                figura.update_yaxes(title=None)
                grafico(figura, "tasas_nivel_gestion", altura=420)
                descargar(corte, NIVEL_GESTION, fuente.origen, "tasas_trayectoria")
            else:
                st.info(SIN_RESULTADOS)
    with caracteristicas:
        st.subheader("Distribuciones por característica")
        _caracteristica(fuente, filtros, anual)


def servicios(fuente, filtros):
    encabezado("Análisis de servicios", "Compara servicios educativos y revisa sus tasas con la matrícula a la vista.",
               fuente.origen, filtros.anios)
    if not filtros.anios:
        st.info(SIN_RESULTADOS)
        return
    if filtros.servicio:
        with st.spinner("Consultando el historial del servicio…"):
            detalle = _totales_anuales(fuente, filtros)
            nombres = fuente.agregados(filtros, por=("anio", "nombre"))
        if not detalle:
            st.info(SIN_RESULTADOS)
            return
        codigo, anexo = filtros.servicio
        st.subheader(nombres[-1]["nombre"])
        st.caption(f"Código modular {codigo} · Anexo {anexo}")
        evolucion(detalle, "servicio_evolucion")
        filas = [{**fila, "cod_mod": codigo, "anexo": anexo} for fila in detalle]
        columnas = ("cod_mod", "anexo", *ANUAL)
        tabla(filas, columnas, "servicio_historial_tabla")
        descargar(filas, columnas, fuente.origen, "historial_servicio")
        return

    selector_anio, selector_tasa = st.columns(2)
    anio = selector_anio.selectbox("Año de análisis", tuple(reversed(filtros.anios)), key="servicio_anio")
    tasas = {"aprobados": "Aprobación", "retirados": "Retiro", "total_atraso": "Atraso"}
    medida = selector_tasa.selectbox("Tasa por servicio", tuple(tasas), index=1,
                                    format_func=tasas.get, key="servicio_tasa")
    anual = replace(filtros, anios=(anio,))
    with st.spinner("Agrupando servicios…"):
        distribucion = fuente.distribucion_servicios(anual, medida)
    if not distribucion:
        st.info(SIN_RESULTADOS)
        return
    st.subheader(f"Distribución de tasas de {tasas[medida].lower()}")
    bandas = ("0 %", ">0–<1 %", "1–<5 %", "5–<10 %", "10–<50 %", "50–<90 %", "90–100 %")
    filas = [
        {"anio": anio, **fila, "intervalo": bandas[fila["tramo"]],
         "grupo": "Menos de 10 matrículas" if fila["matricula_baja"] else "10 matrículas o más"}
        for fila in distribucion
    ]
    figura = px.bar(
        pd.DataFrame(filas), x="intervalo", y="servicios", color="grupo", barmode="stack",
        category_orders={"intervalo": bandas}, color_discrete_sequence=[VERDE, DORADO],
        labels={"intervalo": "Tasa del servicio", "servicios": "Servicios", "grupo": "Matrícula"},
        hover_data={"servicios": ":,.0f"},
    )
    grafico(figura, "servicio_distribucion")
    st.caption("Las tasas con menos de 10 matrículas pueden variar mucho por un solo registro.")
    descargar(filas, ("anio", "intervalo", "grupo", "servicios"), fuente.origen, "distribucion_servicios")

    st.subheader("Servicios para revisión")
    rankings = {"matricula": "Mayor matrícula", "retiro": "Mayor tasa de retiro con al menos 10 matrículas"}
    ranking = st.selectbox("Ordenar por", tuple(rankings), format_func=rankings.get, key="servicios_orden")
    corte = fuente.agregados(
        anual, por=("anio", "cod_mod", "anexo", "nombre", "nivel_nombre", "gestion"), ranking=ranking,
    )
    st.caption("La tabla muestra hasta 100 servicios según el criterio elegido. La distribución abarca todo el corte.")
    if not corte:
        st.info("No hay servicios que cumplan el criterio de revisión.")
        return
    columnas = ("anio", "cod_mod", "anexo", "nombre", "nivel_nombre", "gestion", "matricula",
                "tasa_aprobados", "tasa_retirados", "tasa_total_atraso")
    tabla(corte, columnas, "servicios_ranking_tabla", altura=350)
    descargar(corte, columnas, fuente.origen, "servicios")


def metodologia(fuente, filtros):
    periodos = fuente.periodos()
    encabezado("Datos y metodología", "Procedencia, unidad de análisis y disponibilidad de los indicadores.",
               fuente.origen, tuple(fila["anio"] for fila in periodos))
    origen, unidad = st.columns((1, 1.1))
    with origen, st.container(border=True):
        st.subheader("Origen activo")
        st.success("Lectura verificada")
        if fuente.origen == "csv":
            st.markdown("**Corte publicado:** 28 de marzo de 2025")
            st.write("Exportaciones agregadas del SIAGIE. La copia analítica se preparó a partir de CSV verificados con SHA-256.")
        else:
            st.markdown("**Base:** DW_SIAGIE")
            st.write("Consultas de lectura sobre el modelo estrella. La fecha del catálogo registra el fin de carga en UTC.")
        st.write("Fuente institucional: Unidad de Estadística del Ministerio de Educación del Perú.")
    with unidad, st.container(border=True):
        st.subheader("Unidad de análisis")
        st.write("Año lectivo, código modular, anexo, nivel, edad y tipo de discapacidad registrado.")
        st.write("La matrícula acumulada cuenta matrículas de cada año. Las tasas dividen el conteo de la categoría entre la matrícula del mismo corte.")
        st.write("Los conteos de sexo, nacionalidad, DNI y situación final se publican como distribuciones marginales.")
    st.subheader("Versiones y disponibilidad por año")
    version = [{
        "Año": fila["anio"], "Promoción guiada": "Disponible" if fila["disp_promocion"] else "N/D",
        "Desaprobación": "Disponible" if fila["disp_desaprobacion"] else "N/D",
        "SHA-256 del CSV": fila["huella"] or "N/D",
        "Carga DW (UTC)": fila["actualizado"] or "N/D",
    } for fila in periodos]
    st.dataframe(pd.DataFrame(version), hide_index=True, width="stretch")
    st.caption("Cobertura correspondiente a los registros publicados. Alcance geográfico nacional.")

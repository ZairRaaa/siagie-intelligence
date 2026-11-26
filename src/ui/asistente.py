"""Controles opcionales de GPT y preparación de los datos agregados que se envían."""

import hashlib
import json
from html import escape

import streamlit as st

from src.ai.analisis import ACCIONES, ErrorAsistente, configuracion, generar
from src.ml.artefactos import MODELOS
from src.ui.componentes import ORIGENES, NIVELES, numero, periodo_texto, porcentaje


def datos_resumen(total, anual, filtros, origen):
    hechos = {
        "matricula": f"{numero(total['matricula'])} matrículas registradas",
        "servicios": f"{numero(total['servicios'])} servicios distintos con registros",
        "aprobacion": f"{porcentaje(total['tasa_aprobados'])} de aprobación",
        "retiro": f"{porcentaje(total['tasa_retirados'])} de retiro",
        "atraso": f"{porcentaje(total['tasa_total_atraso'])} de atraso",
    }
    for fila in anual:
        anio = fila["anio"]
        hechos[f"matricula_{anio}"] = f"{anio} · {numero(fila['matricula'])} matrículas"
        if fila["variacion_pct"] is not None:
            hechos[f"variacion_{anio}"] = (
                f"{anio} frente a {anio - 1} · {porcentaje(fila['variacion_pct'], signo=True)} de variación interanual"
            )
    if len(anual) >= 2:
        inicial, ultimo = anual[0], anual[-1]
        diferencia = ultimo["matricula"] - inicial["matricula"]
        hechos["cambio_entre_extremos"] = (
            f"{inicial['anio']} a {ultimo['anio']} · diferencia de {numero(diferencia)} matrículas"
        )
    return {
        "origen": ORIGENES[origen], "periodo": periodo_texto(filtros.anios),
        "nivel": [NIVELES.get(nivel, nivel) for nivel in filtros.niveles or ()],
        "gestion": list(filtros.gestiones or ()), "un_servicio": filtros.servicio is not None,
        "hechos": hechos,
        "alcance": "Registros agregados publicados. Cada matrícula se cuenta en su periodo lectivo.",
    }


def datos_ml(resumen):
    prueba = resumen["particiones"]["prueba"]
    hechos = {
        "seleccion": f"Selección por MAE de validación · {MODELOS[resumen['elegido']]}",
        "pares": f"{numero(prueba['pares'])} pares de servicios observados en ambos años",
        "cobertura": f"{porcentaje(prueba['cobertura_origen_pct'])} de cobertura de servicios de entrada",
    }
    for metrica in resumen["metricas_prueba"]:
        modelo = metrica["modelo"]
        hechos[f"mae_{modelo}"] = f"{MODELOS[modelo]} · MAE {numero(metrica['mae'], 2)} matrículas por servicio"
        hechos[f"rmse_{modelo}"] = f"{MODELOS[modelo]} · RMSE {numero(metrica['rmse'], 2)} matrículas"
        hechos[f"wape_{modelo}"] = f"{MODELOS[modelo]} · WAPE {porcentaje(metrica['wape'])}"
    return {
        "origen": "Métricas auditadas del panel SIAGIE",
        "periodo": f"{prueba['anio_t']} → {prueba['anio_t1']}",
        "hechos": hechos,
        "alcance": "Evaluación histórica única sobre servicios con registros consecutivos. Persistencia usa la matrícula previa.",
    }


def _mostrar(salida, modelo, contexto, clave):
    st.caption(f"Texto generado con {modelo} · cifras calculadas por SIAGIE Intelligence")
    st.html(f"<h4>{escape(salida['titulo'])}</h4>")
    notas = [salida["titulo"]]
    for punto in salida["puntos"]:
        hecho = contexto["hechos"][punto["evidencia"]]
        st.html(f"<p>{escape(punto['texto'])}<br><strong>{escape(hecho)}</strong></p>")
        notas.append(f"{punto['texto']}\n{hecho}")
    st.html(f"<p><em>{escape(salida['alcance'])}</em></p>")
    notas.extend([salida["alcance"], f"Origen: {contexto['origen']} · {contexto['periodo']}", f"Generado con {modelo}"])
    st.download_button(
        "Descargar explicación", "\n\n".join(notas).encode("utf-8-sig"),
        file_name="siagie_explicacion_ia.txt", mime="text/plain", key=f"{clave}_descarga", on_click="ignore",
    )


def asistente(contexto, acciones, clave):
    with st.expander("Asistente GPT"):
        st.caption("Al generar, se envían a OpenAI únicamente indicadores agregados y el contexto del corte.")
        api_key, modelo = configuracion()
        if not api_key:
            st.info("Para activar el asistente, agrega OPENAI_API_KEY a .env.")
            return
        with st.popover("Datos que se enviarán"):
            st.json(contexto)
        with st.form(clave):
            if len(acciones) == 1:
                accion = acciones[0]
                enviar = st.form_submit_button(ACCIONES[accion][0])
            else:
                accion = st.selectbox("Acción", acciones, format_func=lambda id_accion: ACCIONES[id_accion][0])
                enviar = st.form_submit_button("Generar con GPT")
        estado = f"{clave}_respuesta"
        entrada = json.dumps((accion, modelo, contexto), ensure_ascii=False, sort_keys=True)
        firma = hashlib.sha256(entrada.encode("utf-8")).hexdigest()
        if enviar:
            st.session_state.pop(estado, None)
            try:
                with st.spinner("Generando explicación…"):
                    salida, modelo_real = generar(accion, contexto)
                st.session_state[estado] = (firma, salida, modelo_real)
            except ErrorAsistente as error:
                st.warning(str(error))
        anterior = st.session_state.get(estado)
        if anterior is not None and anterior[0] == firma:
            _mostrar(anterior[1], anterior[2], contexto, clave)

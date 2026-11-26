"""Entrada de la aplicación Streamlit para SIAGIE Intelligence."""

from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.data.cache_csv import localizar_cache
from src.data.contrato import Filtros
from src.data.fuente_analitica import FuenteAnalitica
from src.ui.componentes import ESTILO, NIVELES, ORIGENES
from src.ui.pagina_ml import predicciones
from src.ui.paginas import metodologia, resumen, servicios, trayectoria


PAGINAS = {
    "Resumen ejecutivo": resumen, "Matrícula y trayectoria": trayectoria,
    "Análisis de servicios": servicios, "Datos y metodología": metodologia,
}
PAGINA_ML = "ML · Predicciones"


@st.cache_resource(max_entries=4)
def abrir_fuente(origen, version):
    return FuenteAnalitica(origen)


@st.cache_data(ttl=300, max_entries=16, show_spinner=False)
def opciones(_fuente, origen, version, columnas):
    return _fuente.opciones(columnas)


def _version_local(origen):
    if origen == "csv":
        return localizar_cache()[0].name
    ruta = Path(__file__).with_name(".env")
    return ruta.stat().st_mtime_ns if ruta.exists() else None


def filtros_sidebar(fuente, periodos, pagina):
    firma = tuple((fila["anio"], fila["huella"], fila["actualizado"]) for fila in periodos)
    filtro = lambda campos: opciones(fuente, fuente.origen, firma, campos)
    opciones_anios = tuple(fila["anio"] for fila in periodos)
    anios = st.sidebar.multiselect("Años lectivos", opciones_anios, default=opciones_anios, key="anios")
    catalogo = filtro(("nivel", "nivel_nombre"))
    niveles = {fila["nivel"]: NIVELES.get(fila["nivel"], fila["nivel_nombre"]) for fila in catalogo}
    seleccion_nivel = st.sidebar.multiselect(
        "Nivel educativo", tuple(niveles), format_func=niveles.get, placeholder="Todos los niveles", key="niveles",
    )
    gestiones = st.sidebar.multiselect(
        "Gestión", [fila["gestion"] for fila in filtro(("gestion",))],
        placeholder="Todos los tipos de gestión", key="gestiones",
    )
    alcance = Filtros(
        anios=tuple(sorted(anios)), niveles=tuple(seleccion_nivel) or None,
        gestiones=tuple(gestiones) or None,
    )
    edades = discapacidades = None
    if pagina == "Matrícula y trayectoria":
        with st.sidebar.expander("Edad y discapacidad"):
            catalogo_edades = [fila["edad"] for fila in filtro(("edad",))]
            edades = st.multiselect("Edad registrada", catalogo_edades, placeholder="Todas las edades",
                                    format_func=lambda edad: "Desconocida" if edad is None else str(edad),
                                    key="edades")
            tipos = [fila["tipo_discapacidad"] for fila in filtro(("tipo_discapacidad",))]
            discapacidades = st.multiselect("Discapacidad registrada", tipos, placeholder="Todas las categorías",
                                            key="discapacidades")
    servicio = None
    with st.sidebar.expander("Buscar servicio"):
        termino = st.text_input("Nombre, código modular o anexo", max_chars=120, key="buscar_servicio").strip()
        if len(termino) >= 2 and anios:
            resultados = fuente.buscar_servicios(alcance, termino)
            if resultados:
                etiquetas = {
                    (fila["cod_mod"], fila["anexo"]): f"{fila['nombre']} · {fila['cod_mod']}-{fila['anexo']}"
                    for fila in resultados
                }
                servicio = st.selectbox(
                    "Servicio educativo", list(etiquetas), index=None, format_func=etiquetas.get,
                    placeholder="Elige un servicio", key="servicio",
                )
                if len(resultados) == 60:
                    st.caption("Se muestran hasta 60 coincidencias. Refina la búsqueda para ver otras.")
            else:
                st.caption("Sin coincidencias para este corte.")
        else:
            st.caption("Escribe al menos dos caracteres y selecciona un año.")
    return Filtros(
        anios=alcance.anios, niveles=alcance.niveles, gestiones=alcance.gestiones, servicio=servicio,
        edades=tuple(edades) if edades else None,
        discapacidades=tuple(discapacidades) if discapacidades else None,
    )


def main():
    st.set_page_config(page_title="SIAGIE Intelligence", page_icon="📊", layout="wide")
    st.html(f"<style>{ESTILO}</style>")
    with st.sidebar:
        st.html("""
            <div class="siagie-marca">
              <span class="siagie-sello" aria-hidden="true">S</span>
              <div><strong>SIAGIE Intelligence</strong><small>UNCP · Inteligencia de Negocios</small></div>
            </div>
        """)
        pagina = st.radio("Navegación", (*PAGINAS, PAGINA_ML), label_visibility="collapsed", key="pagina")
        if pagina != PAGINA_ML:
            st.divider()
            st.header("Filtros")
            origen = st.selectbox("Fuente de datos", tuple(ORIGENES), format_func=ORIGENES.get, key="origen")
    if pagina == PAGINA_ML:
        predicciones()
        return
    try:
        with st.spinner("Preparando la fuente…"):
            fuente = abrir_fuente(origen, _version_local(origen))
            periodos = fuente.periodos()
            if not periodos:
                st.warning("La fuente seleccionada no contiene años disponibles.")
                return
            filtros = filtros_sidebar(fuente, periodos, pagina)
        PAGINAS[pagina](fuente, filtros)
    except SQLAlchemyError:
        if origen == "sql":
            st.error("No se pudo consultar DW_SIAGIE. Verifica la conexión, la cadena TLS y los permisos de lectura.")
            st.info("Puedes cambiar a CSV SIAGIE verificados en el selector de fuente.")
        else:
            st.error("No se pudo leer la copia analítica de los CSV. Revisa el directorio data/ y el registro local.")
    except (OSError, ValueError):
        st.error("No se pudo preparar el origen. Revisa la configuración local y los archivos de referencia.")


if __name__ == "__main__":
    main()

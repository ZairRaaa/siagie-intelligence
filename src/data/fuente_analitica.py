"""Acceso a agregados y metadatos con procedencia explícita."""

from functools import lru_cache
from time import monotonic

from src.analytics.indicadores import aplicar_indicadores
from src.data.cache_csv import crear_motor_csv
from src.data.consultas import (
    PERIODOS, consulta_agregados, consulta_distribucion, consulta_opciones, consulta_servicios,
)
from src.data.contrato import Filtros
from src.data.sql_server import crear_motor


class FuenteAnalitica:
    def __init__(self, origen):
        self.origen = origen
        self._motor = {"sql": crear_motor, "csv": crear_motor_csv}[origen]()
        self._consulta_cache = lru_cache(maxsize=16)(self._consultar)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()

    def cerrar(self):
        self._consulta_cache.cache_clear()
        self._motor.dispose()

    def periodos(self):
        return self._leer(PERIODOS[self.origen])

    def _leer(self, consulta):
        with self._motor.connect() as conexion:
            return [dict(fila) for fila in conexion.execute(consulta).mappings()]

    def opciones(self, columnas):
        return self._leer(consulta_opciones(self.origen, columnas))

    def buscar_servicios(self, filtros, termino):
        return self._leer(consulta_servicios(self.origen, filtros, termino))

    def distribucion_servicios(self, filtros, medida):
        return self._leer(consulta_distribucion(self.origen, filtros, medida))

    def _consultar(self, filtros, por, _version, _ventana):
        return self._leer(consulta_agregados(self.origen, filtros, por))

    def agregados(self, filtros=Filtros(), por=("anio",), *, ranking=None):
        periodos = {fila["anio"]: fila for fila in self.periodos()}
        anios = tuple(periodos) if filtros.anios is None else filtros.anios
        if set(anios) - periodos.keys():
            raise ValueError("El origen no contiene todos los años solicitados.")
        version = tuple(tuple(fila.values()) for fila in periodos.values())
        por = tuple(por)
        if ranking:
            filas = self._leer(consulta_agregados(self.origen, filtros, por, ranking=ranking))
        elif "cod_mod" in por or "anexo" in por or "nombre" in por:
            # Las consultas de servicios pueden producir cientos de miles de agregados.
            filas = self._consultar(filtros, por, version, None)
        else:
            filas = self._consulta_cache(filtros, por, version, int(monotonic() // 300))
        return aplicar_indicadores(filas, periodos, anios)

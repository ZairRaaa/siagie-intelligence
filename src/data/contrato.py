"""Campos y filtros comunes para SQL Server y los CSV del SIAGIE."""

from dataclasses import dataclass


MEDIDAS_CSV = {
    "matricula": "TotalEstudiantes",
    "cantidad_discapacidad": "Discapacidad",
    "mujeres": "Mujer",
    "hombres": "Hombre",
    "venezolanos": "Venezolanos",
    "peruanos": "Peruanos",
    "otros_extranjeros": "Extranjeros",
    "dni_validado": "DNI_validado",
    "dni_sin_validar": "DNI_SinValidar",
    "sin_dni": "No_DNI",
    "aprobados": "Aprobado",
    "retirados": "Retirado",
    "fallecidos": "Fallecido",
    "requieren_recuperacion": "RequiereRecuperacion",
    "cantidad_situacion_matriculado": "Matriculado",
    "postergan_evaluacion": "PostergaEvaluacion",
    "total_atraso": "tot_atraso",
    "promocion_guiada": "PromocionGuiada",
    "desaprobados": "Desaprobado",
}
DIMENSIONES = (
    "anio", "cod_mod", "anexo", "nombre", "nivel", "nivel_nombre",
    "gestion", "edad", "rango_edad", "tipo_discapacidad",
)
DISPONIBILIDAD = {
    "promocion_guiada": "disp_promocion",
    "desaprobados": "disp_desaprobacion",
}


@dataclass(frozen=True)
class Filtros:
    anios: tuple[int, ...] | None = None
    niveles: tuple[str, ...] | None = None
    gestiones: tuple[str, ...] | None = None
    servicio: tuple[str, str] | None = None
    edades: tuple[int | None, ...] | None = None
    discapacidades: tuple[str, ...] | None = None

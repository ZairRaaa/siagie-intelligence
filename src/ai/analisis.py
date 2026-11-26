"""Solicitudes acotadas a la API Responses para explicar indicadores comprobados."""

import json
import os
from pathlib import Path

from dotenv import dotenv_values
from openai import APIConnectionError, APIStatusError, OpenAI


ROOT = Path(__file__).resolve().parents[2]
MODELO = "gpt-4.1-mini"
ACCIONES = {
    "explicar": ("Explicar este corte", "Interpreta la matrícula, los servicios y las tasas del corte."),
    "comparar": ("Comparar años", "Compara la evolución entre los años seleccionados."),
    "exponer": ("Preparar notas de exposición", "Prepara tres ideas cortas para exponer el corte en voz alta."),
    "ml": ("Interpretar evaluación ML", "Explica la selección temporal, la persistencia y el resultado en prueba."),
}
ESQUEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "puntos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"texto": {"type": "string"}, "evidencia": {"type": "string"}},
                "required": ["texto", "evidencia"],
                "additionalProperties": False,
            },
        },
        "alcance": {"type": "string"},
    },
    "required": ["titulo", "puntos", "alcance"],
    "additionalProperties": False,
}
INSTRUCCIONES = """
Eres un analista de inteligencia de negocios para un proyecto educativo del SIAGIE en Perú.
Responde en español claro. Interpreta los hechos suministrados y la acción indicada.
Devuelve un título, dos o tres puntos breves y una frase de alcance.
Cada punto debe usar como evidencia la clave exacta de un hecho que sostenga su observación.
La interfaz mostrará el hecho y su cifra junto a tu texto. Escribe los textos sin dígitos
ni cifras escritas con palabras. Evita atribuir causas, extrapolar a años no evaluados o inferir datos ausentes.
Utiliza texto plano. Resume la limitación explícita del contexto en la frase de alcance.
"""


class ErrorAsistente(RuntimeError):
    def __init__(self, mensaje, codigo="respuesta_invalida"):
        super().__init__(mensaje)
        self.codigo = codigo


def configuracion():
    archivo = dotenv_values(ROOT / ".env", interpolate=False)
    clave = (os.getenv("OPENAI_API_KEY") or archivo.get("OPENAI_API_KEY") or "").strip()
    modelo = (os.getenv("OPENAI_MODEL") or archivo.get("OPENAI_MODEL") or MODELO).strip() or MODELO
    return clave, modelo


def _error_api(error):
    if error.status_code == 401:
        return ErrorAsistente("OpenAI rechazó la clave. Revisa que esté activa en el proyecto API.", "401")
    if error.status_code in {403, 404}:
        return ErrorAsistente("El proyecto API no tiene acceso a este modelo o a la API Responses.", str(error.status_code))
    if error.status_code == 429:
        if error.code == "credit_balance_exhausted":
            return ErrorAsistente("El saldo prepago de la organización API está agotado.", "credit_balance_exhausted")
        if error.code in {
            "insufficient_quota", "billing_hard_limit_reached", "project_spend_limit_exceeded",
            "organization_spend_limit_exceeded", "organization_usage_limit_exceeded",
        }:
            return ErrorAsistente("La cuenta API alcanzó su cuota. Revisa el saldo y los límites del proyecto.", "cuota")
        return ErrorAsistente("OpenAI devolvió el código 429. Revisa la cuota y los límites del proyecto API antes de reintentar.", "429")
    return ErrorAsistente("OpenAI no pudo completar la solicitud.", str(error.status_code))


def validar_respuesta(texto, hechos):
    try:
        salida = json.loads(texto)
        puntos = salida["puntos"]
        if not isinstance(puntos, list) or not 2 <= len(puntos) <= 3:
            raise ValueError()
        for campo, maximo in ((salida["titulo"], 110), (salida["alcance"], 280)):
            if not isinstance(campo, str) or not 0 < len(campo.strip()) <= maximo or any(c.isdigit() for c in campo):
                raise ValueError()
        for punto in puntos:
            frase = punto["texto"]
            if (punto["evidencia"] not in hechos or not isinstance(frase, str)
                    or not 0 < len(frase.strip()) <= 300 or any(c.isdigit() for c in frase)):
                raise ValueError()
    except (KeyError, TypeError, ValueError) as error:
        raise ErrorAsistente("La explicación no pasó la validación de referencias. Intenta generarla otra vez.") from error
    return salida


def _solicitar(**parametros):
    clave, modelo = configuracion()
    if not clave:
        raise ErrorAsistente("Configura OPENAI_API_KEY en el archivo .env para activar el asistente.", "sin_clave")
    try:
        with OpenAI(api_key=clave, base_url="https://api.openai.com/v1", timeout=20.0, max_retries=0) as cliente:
            respuesta = cliente.responses.create(model=modelo, store=False, **parametros)
    except APIStatusError as error:
        raise _error_api(error) from None
    except APIConnectionError:
        raise ErrorAsistente("No se pudo conectar a OpenAI en el tiempo previsto.", "conexion") from None
    if respuesta.status != "completed" or not respuesta.output_text:
        raise ErrorAsistente("OpenAI no devolvió una explicación completa.")
    return respuesta.output_text, respuesta.model


def comprobar_conexion():
    _, modelo = _solicitar(input="Reply with the word OK.", max_output_tokens=48)
    return modelo


def generar(accion, contexto):
    entrada = json.dumps({"tarea": ACCIONES[accion][1], **contexto}, ensure_ascii=False, allow_nan=False)
    respuesta, modelo = _solicitar(
        instructions=INSTRUCCIONES, input=entrada, max_output_tokens=550,
        text={"format": {"type": "json_schema", "name": "explicacion_siagie",
                         "strict": True, "schema": ESQUEMA}},
    )
    return validar_respuesta(respuesta, contexto["hechos"]), modelo

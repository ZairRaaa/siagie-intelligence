"""Comprueba el acceso a Responses con un mensaje fijo sin datos del proyecto."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from src.ai.analisis import ErrorAsistente, ROOT, comprobar_conexion


def main():
    evidencia = {
        "fecha": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "prueba": "Acceso a Responses con un mensaje fijo sin datos del proyecto",
    }
    try:
        modelo = comprobar_conexion()
        evidencia.update(estado="verificado", modelo=modelo)
    except ErrorAsistente as error:
        evidencia.update(estado="pendiente", codigo=error.codigo, mensaje=str(error))
    archivo = ROOT / "results" / "verificacion_gpt.json"
    archivo.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(evidencia, ensure_ascii=False))
    return int(evidencia["estado"] != "verificado")


if __name__ == "__main__":
    raise SystemExit(main())

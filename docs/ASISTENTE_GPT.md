# Asistente GPT de SIAGIE Intelligence

Extensión opcional de la aplicación local. Streamlit prepara las cifras con los agregados existentes y usa la API Responses de OpenAI para redactar una interpretación corta en español. El modelo predeterminado es GPT-4.1 mini. [API Responses](https://developers.openai.com/api/reference/resources/responses/methods/create) · [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Acciones

| Vista | Acción | Datos de referencia |
|---|---|---|
| Resumen ejecutivo | Explicar este corte | Matrícula, servicios, aprobación, retiro, atraso y serie anual. |
| Resumen ejecutivo | Comparar años | Cifras por año y diferencia entre los extremos de la selección. Requiere dos años con registros. |
| Resumen ejecutivo | Preparar notas de exposición | Ideas breves sustentadas en las cifras del corte. |
| ML · Predicciones | Interpretar evaluación ML | Selección, cobertura y métricas globales de la prueba histórica. |

Cada punto de la respuesta cita un hecho del contexto. La app comprueba que exista esa referencia y muestra la cifra calculada junto al texto. La descarga conserva el texto, las cifras citadas, el periodo y el modelo. El usuario puede contrastar la interpretación con los resultados visibles. [Salidas estructuradas](https://developers.openai.com/api/docs/guides/structured-outputs).

## Configuración y uso

Agrega `OPENAI_API_KEY` al archivo local `.env`. El proyecto usa el SDK `openai`, incluido en `requirements.txt`. `OPENAI_MODEL` es opcional y debe corresponder a un modelo con acceso en el proyecto API.

En la vista deseada, abre **Asistente GPT** y **Datos que se enviarán** para revisar los indicadores. Selecciona la acción y pulsa el botón de generación. Cada pulsación efectúa una solicitud, con un máximo de 550 tokens de salida y un tiempo límite de 20 segundos. Cambiar filtros invalida la explicación previa y espera otra pulsación.

La solicitud se envía desde Python al endpoint oficial de OpenAI. El contexto contiene conteos, tasas, variaciones, periodos y filtros de nivel y gestión. La selección de un servicio se indica mediante un valor booleano. Los códigos de servicio, nombres, registros detallados y archivos locales quedan fuera del contexto. La solicitud configura `store=False`. Cuando falte configuración o la API devuelva un error, el asistente muestra cuál es la condición y los indicadores siguen disponibles. [Manejo de claves](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety).

## Verificación

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m pytest -q tests/test_asistente_gpt.py
& .\.venv\Scripts\python.exe -X utf8 -m scripts.verificar_asistente
```

La segunda instrucción hace una solicitud mínima con un mensaje fijo, sin indicadores del proyecto. El 25 de noviembre de 2026, la API devolvió HTTP 429 con código `credit_balance_exhausted`, que identifica saldo prepago agotado. El informe registra el diagnóstico sin credenciales. La revisión automática bloqueó el ensayo externo con indicadores de SIAGIE hasta contar con autorización específica. Las pruebas de interfaz ejercitan el flujo con un doble del cliente API. [Resultado de conexión](../results/verificacion_gpt.json) · [Códigos de error de OpenAI](https://developers.openai.com/api/docs/guides/error-codes).

# Estado del proyecto · 25 de noviembre de 2026

Fase 1 completada. Se inspeccionaron las referencias en `contexto/`, el Python local y la instancia SQL. Se conciliaron cuatro periodos y se documentó la cobertura para una evaluación temporal por servicio.

El [diagnóstico](DIAGNOSTICO.md) contiene las decisiones, las limitaciones, los comandos de reproducción, las evidencias y el plan por fase.

La base analítica comenzó con la creación de `.venv`, la fijación de dependencias y la verificación de los orígenes desde Python. El resumen CSV reprodujo filas y matrícula en los cuatro años. La prueba SQL desde Python reprodujo el rechazo de la cadena TLS. [Comprobaciones ejecutadas](PRUEBAS.md).

Se implementaron consultas parametrizadas, filtros, agregados con las 19 medidas y tasas ponderadas. El modo CSV usa una copia SQLite derivada y versionada. Se compararon ambos orígenes con lecturas al DW mediante SQLCMD y se ejecutaron pruebas de semántica. [Reglas de indicadores](INDICADORES.md) · [Comprobaciones](PRUEBAS.md).

El dashboard descriptivo está operativo en Streamlit y Plotly con los CSV verificados. Incluye Resumen ejecutivo, Matrícula y trayectoria, Análisis de servicios y Datos y metodología. Se comprobó la descarga desde el navegador y se ejecutaron en el DW las consultas de búsqueda y clasificación. [Arquitectura](ARQUITECTURA.md) · [Evidencias](MANIFIESTO_EVIDENCIAS.md).

Bloque 4 de 5, Machine Learning, completado. El panel de 423 012 servicios-año se concilió fila a fila con el DW. El autor entrenó Ridge y HistGradientBoosting. La persistencia obtuvo el menor MAE en la validación y en la prueba histórica de 2024. [Panel y protocolo](MACHINE_LEARNING.md) · [Resultados](RESULTADOS.md).

Bloque 5 de 5, integración y entrega, completado para el modo CSV verificado. Se comprobaron la página de resultados en el navegador, las métricas globales, los cortes por servicio y una descarga real. El README contiene los comandos y el manifiesto recoge la evidencia del proyecto. [Pruebas](PRUEBAS.md) · [Evidencias](MANIFIESTO_EVIDENCIAS.md).

La conexión directa de Python a SQL Server queda pendiente de resolver la confianza de la cadena TLS. La conciliación de SQL Server se ejecutó con SQLCMD mediante lecturas. El dashboard y la evaluación quedan operativos con los CSV verificados.

Se integró un asistente GPT opcional para interpretar el resumen y la prueba predictiva. El sondeo sin datos del proyecto devolvió HTTP 429 por saldo prepago agotado. Queda pendiente validar la generación real con saldo disponible y autorización explícita para enviar los agregados del corte. [Asistente y verificación](ASISTENTE_GPT.md).

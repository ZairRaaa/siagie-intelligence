# Evidencias técnicas

| N.º | Evidencia | Origen, periodo y alcance |
|---|---|---|
| 1 | [Diagnóstico SQL](../results/diagnostico_sql.txt) | Lecturas de DW_SIAGIE para estructura, cardinalidad y disponibilidad de 2021–2024. 25 de noviembre de 2026. |
| 2 | [Perfil de fuentes](../results/diagnostico_fuentes.json) | CSV originales, huellas SHA-256, calidad y pares consecutivos 2021–2024. 25 de noviembre de 2026. |
| 3 | [Conciliación de indicadores](../results/verificacion_indicadores.json) | Agregados desde SQLite y SQLCMD y comparación con las vistas HEFESTO. 25 de noviembre de 2026. |
| 4 | [Exportación del Resumen ejecutivo](../evidence/siagie_resumen_anual_csv.csv) | Descarga real desde el navegador. CSV verificados, 2021–2024, todos los niveles y gestiones. 25 de noviembre de 2026. |
| 5 | [Consultas del dashboard en SQL Server](../results/verificacion_dashboard_dw.txt) | Búsquedas de servicio, rankings y distribución de retiro para 2024. Ejecutadas con [el SQL de comprobación](../evidence/dashboard_consultas.sql). 25 de noviembre de 2026. |
| 6 | [Panel y particiones de Machine Learning](../results/panel_ml.json) | Conciliación fila a fila de CSV y DW 2021–2024, cobertura temporal y huella de cada Parquet. 25 de noviembre de 2026. |
| 7 | [Verificación previa de Machine Learning](../results/verificacion_ml.txt) | Integridad de las tres particiones y construcción de configuraciones con scikit-learn. Cero ajustes ejecutados. |
| 8 | [Selección y evaluación registradas](../results/referencia_ml/v1_8fb5c53141388938/resumen.json) | Entrenamiento real del autor, 25 de noviembre de 2026, con prueba de matrícula 2024 de 103 856 pares por modelo. |
| 9 | [Auditoría independiente de la ejecución](../results/verificacion_ejecucion_ml.json) | Huellas de archivos, correspondencia de etiquetas, predicciones y recálculo de métricas. |
| 10 | [Figura de comparación del MAE](../evidence/comparacion_mae_2024.png) | Tres comparadores sobre el conjunto completo de prueba 2023→2024. PNG de Matplotlib generado desde los resultados auditados. |
| 11 | [Descarga de predicción de un servicio](../evidence/siagie_prueba_2024_persistencia.csv) | Exportación real del dashboard. Persistencia, código modular 0001506, anexo 000, prueba 2024. |
| 12 | [Pruebas de entrega](../results/pruebas_entrega.txt) | Suite automatizada después de integrar los resultados. 24 pruebas aprobadas. |
| 13 | [Sondeo del asistente GPT](../results/verificacion_gpt.json) | Solicitud de conectividad con mensaje fijo. Evidencia del estado de acceso a Responses, sin cifras del proyecto. |
| 14 | [Pruebas de la extensión GPT](../results/pruebas_asistente_gpt.txt) | Suite automatizada con la extensión instalada. 30 pruebas aprobadas. |

## Material gráfico para el informe

El 25 de noviembre de 2026 se guardaron nueve [capturas horizontales del dashboard](../evidence/capturas). El [Resumen ejecutivo](../evidence/capturas/01_resumen_ejecutivo.png) está en PNG de 1917 × 907 píxeles y las otras ocho capturas en JPEG de 1439 × 810 píxeles. Se tomaron con la aplicación local en ejecución y el origen CSV verificado. El [índice de figuras](INDICE_DE_FIGURAS.txt) indica la vista, el alcance, el lugar sugerido en el informe y una nota para cada imagen. También incluye el [diagrama de la arquitectura](../evidence/arquitectura_siagie.png) y el gráfico de comparación del MAE.

La captura del asistente muestra la interfaz. El registro HTTP del sondeo acredita la falta de saldo de la API.

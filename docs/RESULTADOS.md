# Resultados de SIAGIE Intelligence

## Matrícula y trayectoria registradas

La tabla corresponde al Resumen ejecutivo del dashboard con los CSV verificados, todos los años, niveles y gestiones. Las tasas dividen numeradores agregados entre la matrícula registrada del mismo año. [Exportación desde el navegador](../evidence/siagie_resumen_anual_csv.csv) · [Conciliación con DW_SIAGIE](../results/verificacion_indicadores.json).

| Año | Matrícula | Servicios | Variación interanual | Aprobación | Retiro | Atraso |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 8 173 597 | 105 931 | N/D | 94,33 % | 0,16 % | 3,59 % |
| 2022 | 8 274 834 | 105 488 | +1,24 % | 96,39 % | 0,37 % | 3,06 % |
| 2023 | 8 252 287 | 105 702 | −0,27 % | 95,98 % | 0,84 % | 2,49 % |
| 2024 | 8 153 638 | 105 891 | −1,20 % | 95,82 % | 0,63 % | 2,41 % |

En 2024 se registraron 98 649 matrículas menos que en 2023. La tasa de retiro más alta entre los cuatro periodos fue 0,84 % en 2023. La tasa de atraso registrada descendió de 3,59 % en 2021 a 2,41 % en 2024. Las cifras describen la trayectoria registrada en las fuentes publicadas.

En conjunto se observan 32 854 356 matrículas por año lectivo y 111 049 pares distintos de código modular y anexo. La tarjeta de servicios consolida los pares entre años. El detalle anual cuenta cada par dentro de su propio periodo.

## Evaluación predictiva histórica

El autor ejecutó el entrenamiento y la evaluación el 25 de noviembre de 2026. La prueba usa 103 856 servicios con matrícula registrada tanto en 2023 como en 2024, equivalentes al 98,254 % de los servicios de entrada. Persistencia usa la matrícula de 2023 como estimación de 2024. [Ejecución y versiones](../results/referencia_ml/v1_8fb5c53141388938/resumen.json) · [Protocolo](MACHINE_LEARNING.md).

| Comparador | MAE (matrículas) | RMSE (matrículas) | R² | WAPE |
|---|---:|---:|---:|---:|
| **Persistencia** | **6,95** | **13,95** | **0,9918** | **8,89 %** |
| Ridge | 7,44 | 14,17 | 0,9916 | 9,52 % |
| HistGradientBoosting | 8,33 | 26,18 | 0,9713 | 10,65 % |

La persistencia obtuvo el menor MAE en validación y en la prueba histórica. Su error absoluto promedio fue de 6,95 matrículas por servicio. Los MAE globales de Ridge y de HistGradientBoosting fueron mayores en 0,49 y 1,38 matrículas, respectivamente. El RMSE más alto de HistGradientBoosting indica mayor peso de los errores grandes en esta ejecución. [CSV de métricas](../results/referencia_ml/v1_8fb5c53141388938/metricas_prueba.csv) · [Figura PNG](../evidence/comparacion_mae_2024.png).

En los 24 283 servicios que tenían entre 1 y 9 matrículas en 2023, persistencia tuvo MAE de 1,93 y WAPE de 30,44 %. En los 10 091 servicios de 200 o más matrículas, Ridge tuvo MAE de 21,59 frente a 21,91 de persistencia. Estos cortes describen la heterogeneidad observada en la misma prueba. La decisión global se había fijado por el MAE de validación. [Métricas por segmento](../results/referencia_ml/v1_8fb5c53141388938/metricas_segmentos.csv).

La evaluación se limita a una transición histórica de servicios con registros consecutivos. Para los 1 846 servicios de entrada sin etiqueta de 2024, la documentación registra su exclusión. La evidencia aplica a registros publicados y al escenario retrospectivo de cierre anual. [Cobertura y huellas](../results/panel_ml.json).

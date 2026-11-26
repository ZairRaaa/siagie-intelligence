# Machine Learning · Matrícula siguiente por servicio educativo

## Pregunta y unidad de análisis

Estimar la matrícula registrada de un servicio en el año siguiente a partir de datos agregados del año de entrada. La unidad es una combinación anual de código modular y anexo. Los códigos se conservan como texto de siete y tres dígitos. Los atributos de nivel y gestión corresponden al año de entrada. En 2023→2024 se observaron 55 cambios de nivel y 17 de gestión entre servicios enlazados. Por ello ambos se conservan como atributos temporales.

## Origen, calidad y conciliación

La preparación reunió 423 012 servicios-año, a partir de 2 205 115 registros agregados en la copia SQLite derivada de los cuatro CSV verificados. Las cuatro huellas de fuente coincidieron con los lotes del DW. Las diez columnas del panel se compararon fila por fila contra una exportación de lectura de SQL Server con SQLCMD. Tras la comparación quedaron fijados el panel canónico y los archivos Parquet de cada partición. [Huellas SHA-256, esquema y archivos](../results/panel_ml.json).

Los controles verificaron años esperados, unicidad por servicio y año, formato de claves, ausencia de nulos y matrícula positiva. Aprobación, retiro y atraso quedaron dentro del intervalo entre cero y la matrícula de cada servicio-año. La comparación incluye conteos mediante la consulta SQL utilizada en esta fase. [Consulta de conciliación](../sql/panel_matricula_ml.sql).

## Particiones temporales

| Uso | Año de entrada → objetivo | Pares | Servicios de entrada sin etiqueta | Servicios destino sin antecedente inmediato | Cobertura de servicios de entrada |
|---|---|---:|---:|---:|---:|
| Entrenamiento | 2021 → 2022 | 103 931 | 2 000 | 1 557 | 98,112 % |
| Validación | 2022 → 2023 | 103 722 | 1 766 | 1 980 | 98,326 % |
| Prueba reservada | 2023 → 2024 | 103 856 | 1 846 | 2 035 | 98,254 % |

La etiqueta `matricula_t1` se obtiene mediante una unión uno a uno por código modular y anexo con el año inmediatamente siguiente. La cobertura divide pares enlazados entre servicios del año de entrada. Los pares sin matrícula observada en el año objetivo se excluyen. La evaluación describe los servicios con registros consecutivos y queda sujeta al sesgo de supervivencia. Hay una sola transición de prueba temporal.

## Predictores y protocolo de evaluación

| Uso | Columnas |
|---|---|
| Predictores iniciales | `matricula_t`, `nivel_t`, `gestion_t` |
| Predictores adicionales por evaluar | Tasas de aprobación, retiro y atraso de `t`, en puntos porcentuales de 0 a 100. |
| Etiqueta | `matricula_t1` |
| Trazabilidad | Código modular, anexo, año de entrada y año objetivo. |

La selección de variables e hiperparámetros usa el **MAE de validación**. El preprocesamiento se ajusta dentro de cada pipeline. Se congela una configuración por familia antes de abrir la prueba, con persistencia incluida como comparador. Los conteos, tasas y atributos educativos del año objetivo quedan fuera de los predictores. Las tasas candidatas corresponden al escenario retrospectivo de cierre anual. Las fuentes locales carecen de fechas operativas de disponibilidad por variable.

| Familia | Configuraciones |
|---|---|
| Persistencia | La estimación es la matrícula del año de entrada. |
| Ridge | Alfa 1 o 10. Predictores iniciales con o sin las tres tasas. Imputación por mediana y escalado para variables numéricas. |
| HistGradientBoosting | 15 o 31 hojas máximas, 100 iteraciones y semilla 42. Predictores iniciales con o sin las tres tasas. Imputación numérica por mediana y sin parada anticipada. |

Ridge y HistGradientBoosting imputan la categoría más frecuente y codifican nivel y gestión con one-hot. Las configuraciones se evalúan primero con entrenamiento 2021→2022 y validación 2022→2023. Los finalistas de Ridge y árboles se reajustan con ambas transiciones y se evalúan junto con persistencia sobre las mismas claves de 2023→2024. Las estimaciones negativas se recortan a cero antes de medir errores. Los valores permanecen continuos para evaluación. [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) · [HistGradientBoosting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html).

Se calculan MAE y RMSE en matrículas, R² y WAPE como porcentaje del total observado. El signo del error es estimado menos observado. El resultado incluye cortes por nivel del año de entrada y tamaños de 1–9, 10–49, 50–199 y 200 o más matrículas. La aplicación distingue el modelo seleccionado en validación de su desempeño posterior frente a la persistencia.

## Ejecutar el entrenamiento local

El autor ejecutó el entrenamiento real en PowerShell el 25 de noviembre de 2026. La ejecución registrada utilizó dos hilos y tomó 13,898 s. Los comandos desde la raíz del proyecto son:

```powershell
# Comprobación opcional, sin ajustar modelos
& .\.venv\Scripts\python.exe -X utf8 -m scripts.entrenar_matricula --verificar

# Entrenamiento, validación y evaluación
& .\.venv\Scripts\python.exe -X utf8 -m scripts.entrenar_matricula
```

El comando usa dos hilos internos por defecto y muestra cada candidato en la consola. El tiempo total se registra al finalizar. Se permite elegir otro límite con `--hilos` antes de iniciar. Si se interrumpe después de guardar la selección, el mismo comando recupera la configuración congelada con las mismas versiones y el mismo límite de hilos.

La ejecución genera un directorio versionado bajo `results/ml/` con `seleccion.json`, tres CSV de métricas, las predicciones en Parquet y los pipelines propios en Joblib. Publica `resumen.json` al final. Si este archivo existe, el comando reutiliza la ejecución registrada. La página **ML · Predicciones** lee métricas, artefactos de datos y huellas de esta ejecución. Los filtros de esa página cambian los cortes de predicciones. Las métricas globales conservan todos los pares de la prueba. 

La verificación previa cargó entrenamiento y validación y comprobó la huella del archivo de prueba. Su salida registra cero modelos ajustados antes de la ejecución del autor. [Verificación previa](../results/verificacion_ml.txt).

## Resultado de la ejecución

Se compararon nueve configuraciones en validación. La persistencia fue seleccionada con MAE 7,24. Los finalistas de las otras familias fueron Ridge con alfa 1 y las tasas de entrada, e HistGradientBoosting con 15 hojas máximas y predictores iniciales. Sus MAE de validación fueron 8,65 y 9,46. [Selección congelada](../results/referencia_ml/v1_8fb5c53141388938/seleccion.json) · [Métricas de validación](../results/referencia_ml/v1_8fb5c53141388938/metricas_validacion.csv).

La evaluación de 2024 confirmó el menor error global para persistencia. Ridge e HistGradientBoosting se ajustaron y evaluaron en los mismos 103 856 pares. El modelo de referencia recomendado para este protocolo es persistencia. [Comparación de prueba y discusión](RESULTADOS.md) · [Métricas de prueba](../results/referencia_ml/v1_8fb5c53141388938/metricas_prueba.csv).

La auditoría verificó seis huellas, 311 568 predicciones, treinta cortes y la coincidencia exacta de cada objetivo con la partición de prueba. Para repetir la auditoría y regenerar la figura a partir de los archivos guardados:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m scripts.verificar_ejecucion_ml --figura
```

El comando lee las predicciones y recalcula sus métricas. [Auditoría](../results/verificacion_ejecucion_ml.json).

## Reproducción de la preparación

Desde la raíz del proyecto, con el entorno virtual instalado y acceso a la instancia local mediante autenticación integrada:

```powershell
New-Item -ItemType Directory -Force data/ml | Out-Null
$cliente = (Get-Command sqlcmd.exe).Source
& $cliente -S 'SERVIDOR_LOCAL\SQLEXPRESS' -E -d DW_SIAGIE -l 8 -t 120 -b -W -h -1 -s '|' -f 65001 -u -i sql/panel_matricula_ml.sql -o data/ml/panel_dw.txt
if ($LASTEXITCODE -ne 0) { throw 'Falló la exportación de lectura de SQL Server.' }
& .\.venv\Scripts\python.exe -m scripts.preparar_panel_ml --dw data/ml/panel_dw.txt
& .\.venv\Scripts\python.exe -m pytest -q tests/test_panel_ml.py
```

El archivo `results/panel_ml.json` apunta a la versión preparada y registra las huellas de los Parquet. Los archivos masivos se generan localmente bajo `data/ml/`. Repetir la preparación ante la misma versión verifica la coincidencia de los artefactos existentes.

Para reproducir las particiones en un equipo con los CSV oficiales, ejecuta `python -m scripts.preparar_panel_ml --solo-csv` con la `.venv`. La opción verifica la concordancia con las huellas de la auditoría histórica y conserva su registro.

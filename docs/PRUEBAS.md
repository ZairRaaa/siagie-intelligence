# Comprobaciones de la base analítica

## Entorno y fuentes · 25 de noviembre de 2026

| Comando o control ejecutado | Resultado |
|---|---|
| `python -m venv .venv` | Entorno local creado con Python 3.12.3 x64. |
| `.venv\Scripts\python.exe -m pip check` | Salida 0. Sin dependencias rotas. Las versiones instaladas quedaron en `requirements.txt`. |
| `.venv\Scripts\python.exe -m scripts.verificar_origen --origen csv` | Salida 0. Cuatro huellas aceptadas y cuatro periodos devueltos. [Salida JSON](../results/verificacion_origen_csv.json). |
| Comparación de pares `(filas, matricula)` por año | Coincidencia exacta entre el JSON y la [salida SQL del diagnóstico](../results/diagnostico_sql.txt) para 2021–2024. |
| `.venv\Scripts\python.exe -m scripts.verificar_origen --origen sql` | Salida 1 con SQLSTATE `08001` y código `-2146893019`. El controlador llegó a la validación del certificado y rechazó su cadena de confianza. La consulta de matrícula vía Python queda pendiente de resolver TLS. |
| `sqlcmd.exe -S 'lpc:SERVIDOR_LOCAL\SQLEXPRESS' -E -N -d DW_SIAGIE -l 8 -b` con un SELECT | Salida 1 con el mismo rechazo de certificado al solicitar cifrado en la instancia local. |

La conexión usa la cadena ODBC directa del dialecto SQL Server y mantiene `Encrypt=yes` con `TrustServerCertificate=no`. [SQLAlchemy, dialecto SQL Server](https://docs.sqlalchemy.org/en/20/dialects/mssql.html) · [Microsoft, opciones del cliente ODBC](https://learn.microsoft.com/en-us/sql/connect/odbc/dsn-connection-string-attribute)

## Indicadores y filtros · 25 de noviembre de 2026

La copia analítica SQLite contiene 2 205 115 filas y ocupa 438 681 600 bytes. Su nombre incluye la huella del manifiesto y la versión de normalización. El proceso verificó las cuatro huellas y publicó el archivo tras completar la carga. El caché en memoria conserva hasta 16 resultados pequeños por instancia de origen, filtros, dimensiones, versión y ventana de hasta cinco minutos. Los resultados agrupados por servicio se consultan bajo demanda.

`python -m pytest -q` ejecutado con la `.venv` devolvió **6 pruebas aprobadas** en 48,97 s. Se cubrieron totales, tasas ponderadas, disponibilidad parcial, edad cero y desconocida, filtros sin resultados, claves con ceros iniciales, variación con salto de años y parámetros SQL enlazados.

El módulo SQL generó siete consultas conciliadas mediante SQLCMD con autenticación de Windows. El CSV devolvió los mismos 19 conteos, filas y servicios para los cortes comparados. También coincidieron las medidas comunes de las vistas HEFESTO en los cuatro grupos anuales y los 72 grupos por año, nivel y gestión. En esta ejecución, el resumen anual consultó la copia CSV en 4,081 s y el corte de un servicio en 0,002 s. La conexión Python conserva la validación del certificado y continúa pendiente de resolver TLS. [Salida SQL](../results/verificacion_indicadores_dw.txt) · [Conciliación y tiempos observados](../results/verificacion_indicadores.json).

Reproducción desde PowerShell:

```powershell
$python = '.\.venv\Scripts\python.exe'
& $python -m pytest -q
& $python -m scripts.verificar_indicadores preparar data/verificacion_indicadores_dw.sql
$cliente = (Get-Command sqlcmd.exe).Source
& $cliente -S 'SERVIDOR_LOCAL\SQLEXPRESS' -E -d DW_SIAGIE -l 8 -t 120 -b -W -h -1 -s '|' -f 65001 -u -i data/verificacion_indicadores_dw.sql -o results/verificacion_indicadores_dw.txt
& $python -m scripts.verificar_indicadores comparar results/verificacion_indicadores_dw.txt results/verificacion_indicadores.json
```

## Dashboard · 25 de noviembre de 2026

Se ejecutó Streamlit 1.67.0 con Plotly 6.9.0 en la interfaz local. La ruta de salud devolvió `ok`. El Resumen ejecutivo renderizó cinco indicadores y dos gráficos con datos de 2021–2024. La descarga generó un CSV con los cuatro años y las tasas de la selección. [Archivo descargado](../evidence/siagie_resumen_anual_csv.csv).

La suite completa devolvió **12 pruebas aprobadas** en 91,45 s. Las comprobaciones de la interfaz cubren navegación, filtro de año, selección vacía, disponibilidad parcial, comparación por nivel y gestión, búsqueda, historial, ranking de servicios y formato de exportación. [Salida de pytest](../results/pruebas_dashboard.txt).

Se ejecutó el SQL de búsqueda y agrupación para 2024 mediante SQLCMD y se comparó con la copia CSV. Coincidieron la búsqueda exacta por código, las tres coincidencias por nombre, el orden y valores de las 100 filas de cada ranking y los 11 grupos de la distribución por retiro. [SQL usado](../evidence/dashboard_consultas.sql) · [Salida del DW](../results/verificacion_dashboard_dw.txt).

La ejecución de Streamlit seleccionó SQL Server y mostró el aviso de conexión, seguido de la recuperación del resumen al cambiar a CSV. Persiste el requisito de validar la cadena TLS para consultar SQL desde la aplicación.

## Preparación del panel predictivo · 25 de noviembre de 2026

Se conciliaron las diez columnas de las 423 012 filas anuales entre CSV y DW mediante SQLCMD. Se ejecutaron cuatro pruebas de preparación para claves repetidas, conteos incompatibles, cambio de atributos y enlaces consecutivos con ausencias. [Registro del panel](../results/panel_ml.json) · [Comandos reproducibles](MACHINE_LEARNING.md).

## Verificación previa de Machine Learning

`python -X utf8 -m scripts.entrenar_matricula --verificar` comprobó scikit-learn 1.9.1, los pares de entrenamiento y validación, y la huella de la prueba reservada. La ejecución registró cero ajustes. [Salida de la verificación](../results/verificacion_ml.txt).

La suite completa devolvió **24 pruebas aprobadas** en 106,28 s. Se probaron los cálculos y la selección, el orden de congelación, el estado pendiente y la publicación y lectura en el dashboard con un conjunto mínimo de pruebas aisladas. El rendimiento predictivo queda pendiente del ajuste real. [Salida de pytest](../results/pruebas_ml.txt).

## Integración de la ejecución real

La auditoría independiente verificó seis archivos por SHA-256 y confirmó la correspondencia de las claves, atributos de entrada y valores observados de cada comparador con la prueba reservada. Se recalcularon las métricas globales y de 30 cortes a partir de 311 568 predicciones publicadas. [Registro de auditoría](../results/verificacion_ejecucion_ml.json).

La página ML mostró la comparación de los tres modelos y el tiempo de ejecución de 13,90 s. Al buscar `0001506-000`, el navegador mostró un par y mantuvo el MAE global de 6,95. Se descargó su predicción de persistencia y el CSV coincidió con la fila correspondiente del Parquet. [Comprobación de Streamlit](../results/prueba_dashboard_ml_real.txt) · [Descarga real](../evidence/siagie_prueba_2024_persistencia.csv).

El comando `python -X utf8 -m scripts.verificar_ejecucion_ml --figura` exportó la figura del MAE con Matplotlib 3.11.2. [Figura generada](../evidence/comparacion_mae_2024.png).

La ejecución final de la suite devolvió **24 pruebas aprobadas** en 193,47 s. La verificación de dependencias con `pip check` devolvió salida 0. [Registro final de pytest](../results/pruebas_entrega.txt).

## Asistente GPT opcional

Seis pruebas específicas verificaron que las solicitudes ocurran por pulsación, que el contexto se limite a agregados, que se rechacen referencias ajenas y cifras añadidas y que los cambios de filtros invaliden la explicación anterior. El SDK y la interfaz se probaron con un doble sin uso de la clave real.

La suite completa devolvió **30 pruebas aprobadas** en 238,26 s. [Registro de pytest](../results/pruebas_asistente_gpt.txt).

La prueba de conectividad enviando solo un texto fijo devolvió HTTP 429 con `credit_balance_exhausted`. La revisión automática bloqueó el ensayo externo con indicadores reales, por lo que queda pendiente validar una respuesta de OpenAI a los datos del dashboard. [Diagnóstico de la solicitud](../results/verificacion_gpt.json).

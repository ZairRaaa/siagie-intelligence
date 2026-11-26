# SIAGIE Intelligence · Diagnóstico inicial

**UNCP · Inteligencia de Negocios · 25 de noviembre de 2026**  
**Autor del proyecto:** Zair Ken Rojas Cerron. **Alcance de esta fase:** inspección local, consultas de lectura, conciliación y diseño del protocolo. 

## 1. Dictamen

El DW está en línea. Los cuatro CSV, la tabla de hechos y el cierre histórico coinciden en filas y matrícula por año. El panel permite evaluar retrospectivamente la matrícula siguiente por servicio. El rendimiento predictivo queda por medir. Para conectar la aplicación con cifrado y validación de identidad del servidor queda pendiente resolver la confianza del certificado. Los CSV conciliados permiten avanzar en paralelo con el mismo conjunto de registros.

## 2. Antecedentes y fuentes

Se encontró la especificación en `contexto/AGENTS.md`. Las referencias originales están bajo `contexto/`. La propuesta, el README y el cierre describen el paso de preguntas de negocio a indicadores, dimensiones, ETL y validación HEFESTO. Los scripts SQL 02, 05, 06, 09 y 10 documentan el esquema, las conciliaciones, las dos vistas, las consultas analíticas y la inspección de metadatos. La aplicación puede reutilizar estas definiciones sin recargar el almacén.

El informe Word de la semana 7 documenta el DW. El PDF de semana 12 (21 páginas) trata el uso de DAX con el cubo OLAP. El PBIX contiene una definición de informe, visuales y conexiones. Se inspeccionó su contenedor, sin ejecutar Power BI ni certificar la actualización del cubo.

La hoja `DiccionarioDatos` tiene 27 filas incluyendo cabecera. Define `TotalEstudiantes` como matrícula, `Matriculado` como situación final y `Extranjeros` como extranjeros excepto venezolanos. La edad se calcula al 31 de marzo. Los metadatos atribuyen el conjunto a la Unidad de Estadística del MINEDU, edición 2025, con fecha 28 de marzo de 2025, frecuencia anual y cobertura nacional declarada. La evidencia local no establece cuándo estuvo disponible cada variable de 2021–2023 para una decisión en tiempo real.

## 3. Entorno y conexión

| Componente | Resultado observado |
|---|---|
| Sistema | Equipo SERVIDOR_LOCAL, Windows x64, compilación 26300. Python de usuario 3.12.3 de 64 bits y Git 2.46.1.windows.1. Usar `python`; el lanzador `py -0p` no enumeró intérpretes en la sesión aislada. |
| Análisis | Importación correcta de pandas 2.2.2, NumPy 2.4.6, scikit-learn 1.5.0, Plotly 6.2.0 y joblib 1.4.2. PyArrow 22.0.0 instalado. |
| Dependencias pendientes | Streamlit, SQLAlchemy, pyodbc y pytest ausentes del Python inspeccionado. No se instaló software ni se creó el entorno virtual. |
| Motor y cliente | SQL Server 2022 Developer Edition x64, 16.0.1000.6, instancia nominal `SERVIDOR_LOCAL\SQLEXPRESS`. ODBC Driver 17 y SQLCMD.EXE disponibles. Servicio de esa instancia activo, instancia predeterminada y SQL Browser detenidos. |
| Acceso efectivo | La sesión aislada agotó el tiempo de conexión. La comprobación local autorizada con SQLCMD, autenticación integrada y base explícita devolvió el esquema y los agregados. Solo se ejecutaron lecturas. Los privilegios efectivos de la cuenta podrían ser más amplios. |
| TLS | La prueba adicional con `-N` falló con «La cadena de certificación fue emitida por una entidad en la que no se confía». Se verificó acceso con las opciones predeterminadas del cliente. La plantilla `.env.example` exige cifrado y validación. Para el despliegue, validar con el administrador la cadena y el nombre del certificado, repetir la prueba y después probar SQLAlchemy/pyodbc. |

## 4. Esquema y conciliación

El grano observado es año, servicio (código modular y anexo), nivel, edad y tipo de discapacidad. `dw.FactMatricula` tiene 19 medidas, referencias al lote y al registro de origen y cinco dimensiones: año, servicio anual, nivel, edad y discapacidad. Sus siete claves foráneas están habilitadas y son de confianza para SQL Server. Se encontraron cero grupos duplicados al grano dimensional, cero claves naturales de servicio repetidas dentro de un año y cero hechos cuyo año difiera del año del servicio enlazado. Existen `stg.Matricula`, `etl.Lote`, `etl.IntentoCarga`, `dw.vw_ResumenAnual` y `dw.vw_MatriculaNivelGestion`.

| Año | Filas CSV = hechos DW | Matrícula CSV = DW | Servicios con registros | Edad vacía en CSV = hechos con edad desconocida | Tipo de discapacidad vacío en CSV |
|---|---:|---:|---:|---:|---:|
| 2021 | 566 359 | 8 173 597 | 105 931 | 5 | 495 330 |
| 2022 | 558 785 | 8 274 834 | 105 488 | 0 | 490 216 |
| 2023 | 544 834 | 8 252 287 | 105 702 | 0 | 481 172 |
| 2024 | 535 137 | 8 153 638 | 105 891 | 1 | 473 294 |
| Acumulado | **2 205 115** | **32 854 356** | — | **6** | **1 940 012** |

La matrícula acumulada cuenta matrículas por periodo. Un estudiante puede contribuir en varios periodos. Los controles comparan agregados anuales y estructura. Una conciliación registro a registro entre los dos soportes excede esta verificación.

**Calidad de los CSV.** Se leyeron las cuatro exportaciones completas en UTF-8 con BOM, conservando identificadores como texto. Las cuatro huellas y cabeceras coinciden con el manifiesto anterior. Cada año contiene 26 columnas. No aparecieron duplicados al grano, medidas vacías, negativas o superiores al total. Por fila cuadran sexo, nacionalidad, documento y situaciones finales con la matrícula. Los únicos vacíos de origen corresponden a las dos columnas incluidas en la tabla. Estos resultados concuerdan con la auditoría de referencia. La categoría de discapacidad vacía debe distinguirse del literal de tipo sin especificación. En el DW la edad desconocida usa la clave −1.

**Disponibilidad temporal.** En los hechos, promoción guiada tiene valor para todas las filas de 2021–2022 y ninguna de 2023–2024. Desaprobación presenta el patrón inverso. La vista anual conserva NULL para los periodos sin medida. Para selecciones mixtas se comprobarán las banderas de todos los años seleccionados. Las tasas se calculan como 100 × suma del numerador / suma de matrícula, con N/D para denominador cero. Los conteos marginales impiden deducir aprobación por sexo u otros cruces individuales.

**Diferencia frente al diseño documentado.** La instancia contiene `stg.PadronGeo` y `stg.PadronGeoRaw` con 180 943 filas cada una. `DimServicio` incorpora CODGEO, códigos de departamento y provincia, y nombres de departamento, provincia y distrito. La existencia de estos campos no acredita procedencia, vigencia por año ni correspondencia unívoca. El alcance inicial sigue siendo nacional. Una ampliación geográfica requeriría validar esas propiedades y obtener autorización.

## 5. Viabilidad de Machine Learning

La unidad propuesta es **servicio por año**. Se sumará matrícula por `cod_mod` y `anexo`, conservando ceros iniciales. En cada año hay un solo nivel, nombre y gestión por clave. En el enlace 2023–2024 se observaron 55 cambios de nivel y 17 de gestión. Incluir el nivel en la clave rompería seguimientos que sí existen. Se usarán los atributos conocidos en el año de origen. La clave sirve para enlazar y auditar.

| Entrada → objetivo | Uso | Pares observados | Servicios de origen sin etiqueta | Servicios destino sin antecedente inmediato | Cobertura del origen |
|---|---|---:|---:|---:|---:|
| 2021 → 2022 | Entrenamiento inicial | 103 931 | 2 000 | 1 557 | 98,112 % |
| 2022 → 2023 | Validación y selección | 103 722 | 1 766 | 1 980 | 98,326 % |
| 2023 → 2024 | Prueba final reservada | 103 856 | 1 846 | 2 035 | 98,254 % |

La cobertura mide claves comunes divididas por servicios del año de entrada. Se excluyen las ausencias sin imputar matrícula cero. Los resultados representarán servicios observados en años consecutivos y quedan sujetos a sesgo de supervivencia. Hay tres transiciones anuales y una sola prueba temporal, aunque cada partición tenga más de cien mil pares.

**Regresión prioritaria.** Comparar persistencia con Ridge y un modelo de árboles. Usar matrícula, nivel y gestión del año de entrada. Evaluar en validación si aportan las tasas históricas disponibles al corte. Evitar exigir cambio respecto a un año previo en el modelo principal porque eliminaría el entrenamiento de 2021. Excluir identificadores, nombres, discapacidad, DNI y nacionalidad como predictores. Ajustar transformaciones dentro del pipeline de entrenamiento y fijar configuración, semilla y tratamiento de negativos antes del test. Se puede reajustar con las primeras dos transiciones. Evaluar una sola vez la última con MAE, RMSE y R², incluyendo la línea base sobre las mismas claves. Guardar errores por nivel y tamaño, además de las métricas globales. No se ajustaron modelos ni se calcularon métricas predictivas en esta fase.

**Extensiones.** K-Means es técnicamente evaluable en un corte anual. En 2024 hay 27 381 servicios con menos de diez matrículas y ninguno con matrícula cero. La interpretación de tasas para servicios pequeños exige análisis de sensibilidad, escalado y revisión de perfiles y silhouette antes de publicar grupos. Para predecir retiro agregado existe numerador y denominador, pero falta perfilar los ceros de retiro por servicio y la estabilidad de su tasa. Ambas extensiones quedan después del núcleo. Un eventual valor 2025 sería una estimación posterior al último dato observado, sin validación contra 2025 en estas fuentes.

## 6. Plan de implementación y aceptación

| Orden | Trabajo previsto | Evidencia que permitirá aceptar la fase |
|---|---|---|
| 1. Acceso reproducible | Crear .venv en Python 3.12, instalar y fijar versiones probadas. Resolver TLS, validar acceso integrado de lectura con SQLAlchemy y pyodbc. Implementar fuente CSV explícita usando las huellas verificadas. | Instalación reproducida, consulta de prueba, origen y versión visibles. Comparación de filas, matrícula e indicadores por año y nivel entre orígenes. |
| 2. Base analítica | Consultas parametrizadas, agregación en SQL, caché por versión/origen/filtros. Definir catálogo de indicadores y filtros compatibles. | Pruebas de sumas ponderadas, división por cero, selección vacía, desconocidos, disponibilidad parcial y variación entre años consecutivos. Conciliar resultados con las consultas HEFESTO. |
| 3. Interfaz | Construir Resumen, Matrícula y trayectoria, Servicios y Datos y metodología en Streamlit/Plotly. Añadir búsqueda por código/anexo, filtros y exportación CSV. | Probar totales y exportaciones filtradas con el origen activo, errores de conexión y estados sin resultados. Registrar capturas reales y tiempos de respuesta. |
| 4. Evaluación predictiva | Reconciliar el panel SQL con las claves y etiquetas CSV antes del ajuste. Construir datasets temporales, ejecutar línea base y candidatos fuera de Streamlit y congelar selección. | Huellas, variables, versiones, semilla, particiones, métricas, predicciones individuales por **servicio**, residuos y comparación con persistencia. Documentar si el modelo no mejora la base. |
| 5. Integración y entrega | Integrar resultados históricos en la página ML. Distinguir métricas globales de cortes filtrados. Reproducir pruebas desde instalación limpia. Evaluar extensiones según tiempo para la presentación del 2 de diciembre. | README con comandos ejecutados, pruebas registradas, artefactos propios de modelo y manifiesto de evidencias para el informe. La interfaz debe funcionar sin reentrenar en cada filtro. |

## 7. Reproducción y evidencia

Desde la raíz del proyecto, en PowerShell y con acceso local integrado a la instancia:

```powershell
python --version
python -m pip list
Get-Service -Name 'MSSQL*','SQLBrowser'
python scripts/diagnostico_fuentes.py
$cliente = (Get-Command sqlcmd.exe).Source
& $cliente -S 'SERVIDOR_LOCAL\SQLEXPRESS' -E -d DW_SIAGIE -l 8 -b -W -s '|' -i sql/diagnostico_lectura.sql
& $cliente -S 'SERVIDOR_LOCAL\SQLEXPRESS' -E -N -d DW_SIAGIE -l 8 -b -Q 'SELECT DB_NAME()'
```

El script Python requiere pandas y escribe un resumen agregado. El archivo SQL contiene lecturas y devuelve resultados por consola. La última instrucción reproduce la prueba específica de TLS.

| Evidencia | Contenido |
|---|---|
| [Perfil de los cuatro CSV](../results/diagnostico_fuentes.json) | Huellas completas, controles de calidad, servicios por año y cobertura de cada transición. |
| [Salida SQL de esta fase](../results/diagnostico_sql.txt) | Instancia, versión, esquema real, tipos y nulabilidad, claves foráneas, controles del grano, disponibilidad y conciliación. |
| [Manifiesto histórico](../contexto/resultados/manifiesto_fuentes.json) y [cierre de idempotencia](../contexto/resultados/cierre/08_idempotencia.log) | Versiones de fuente y totales históricos para contraste. |
| [Auditoría anterior](../contexto/auditoria_datos.json) | Perfil de referencia y reglas empleadas en HEFESTO. |

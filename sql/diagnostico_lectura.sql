SET NOCOUNT ON;
SELECT @@SERVERNAME AS servidor, DB_NAME() AS base,
       SERVERPROPERTY('ProductVersion') AS version, SERVERPROPERTY('Edition') AS edicion;
SELECT SCHEMA_NAME(o.schema_id) AS esquema, o.name AS objeto, o.type_desc AS tipo
FROM sys.objects AS o
WHERE SCHEMA_NAME(o.schema_id) IN ('stg','etl','dw') AND o.type IN ('U','V')
ORDER BY esquema, objeto;
SELECT OBJECT_NAME(c.object_id) AS tabla, c.name AS columna, TYPE_NAME(c.user_type_id) AS tipo,
       c.is_nullable AS admite_null
FROM sys.columns AS c JOIN sys.tables AS t ON t.object_id=c.object_id
WHERE SCHEMA_NAME(t.schema_id)='dw' ORDER BY tabla,c.column_id;
SELECT name, is_disabled, is_not_trusted FROM sys.foreign_keys
WHERE parent_object_id=OBJECT_ID('dw.FactMatricula') ORDER BY name;
SELECT a.anio, a.disp_promocion, a.disp_desaprobacion, COUNT_BIG(*) AS filas,
       SUM(CONVERT(bigint,f.total_estudiantes)) AS matricula,
       COUNT(DISTINCT f.id_servicio) AS servicios,
       SUM(CASE WHEN f.id_edad=-1 THEN 1 ELSE 0 END) AS edad_desconocida,
       COUNT(f.promocion_guiada) AS filas_promocion, COUNT(f.desaprobados) AS filas_desaprobacion
FROM dw.FactMatricula AS f JOIN dw.DimAnio AS a ON a.anio=f.anio
GROUP BY a.anio,a.disp_promocion,a.disp_desaprobacion ORDER BY a.anio;
SELECT COUNT_BIG(*) AS grupos_duplicados FROM (
    SELECT anio,id_servicio,id_nivel,id_edad,id_discapacidad FROM dw.FactMatricula
    GROUP BY anio,id_servicio,id_nivel,id_edad,id_discapacidad HAVING COUNT_BIG(*)>1
) AS d;
SELECT COUNT_BIG(*) AS servicios_anuales_duplicados FROM (
    SELECT anio,cod_mod,anexo FROM dw.DimServicio
    GROUP BY anio,cod_mod,anexo HAVING COUNT_BIG(*)>1
) AS d;
SELECT COUNT_BIG(*) AS hechos_con_anio_servicio_distinto
FROM dw.FactMatricula AS f JOIN dw.DimServicio AS s ON s.id_servicio=f.id_servicio
WHERE f.anio<>s.anio;
SELECT anio,matricula,promocion_guiada,desaprobados FROM dw.vw_ResumenAnual ORDER BY anio;
SELECT (SELECT COUNT_BIG(*) FROM stg.PadronGeo) AS filas_padron,
       (SELECT COUNT_BIG(*) FROM stg.PadronGeoRaw) AS filas_padron_raw;

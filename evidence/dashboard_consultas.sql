SET NOCOUNT ON;
PRINT 'CASO:busqueda_codigo';

        SELECT TOP (60) cod_mod, anexo, MIN(nombre) AS nombre
        FROM (
    SELECT f.anio AS anio, s.cod_mod AS cod_mod, s.anexo AS anexo, s.nombre AS nombre, n.codigo AS nivel, n.descripcion AS nivel_nombre, s.gestion AS gestion, e.edad AS edad, e.rango AS rango_edad, d.tipo AS tipo_discapacidad, f.total_estudiantes AS matricula, f.cantidad_discapacidad, f.mujeres, f.hombres, f.venezolanos, f.peruanos, f.otros_extranjeros, f.dni_validado, f.dni_sin_validar, f.sin_dni, f.aprobados, f.retirados, f.fallecidos, f.requieren_recuperacion, f.cantidad_situacion_matriculado, f.postergan_evaluacion, f.total_atraso, f.promocion_guiada, f.desaprobados
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos

        WHERE (anio IN (2024)) AND cod_mod=N'0001506'
        GROUP BY cod_mod, anexo
        ORDER BY cod_mod, anexo
        
    ;
GO
PRINT 'CASO:busqueda_nombre';

        SELECT TOP (60) cod_mod, anexo, MIN(nombre) AS nombre
        FROM (
    SELECT f.anio AS anio, s.cod_mod AS cod_mod, s.anexo AS anexo, s.nombre AS nombre, n.codigo AS nivel, n.descripcion AS nivel_nombre, s.gestion AS gestion, e.edad AS edad, e.rango AS rango_edad, d.tipo AS tipo_discapacidad, f.total_estudiantes AS matricula, f.cantidad_discapacidad, f.mujeres, f.hombres, f.venezolanos, f.peruanos, f.otros_extranjeros, f.dni_validado, f.dni_sin_validar, f.sin_dni, f.aprobados, f.retirados, f.fallecidos, f.requieren_recuperacion, f.cantidad_situacion_matriculado, f.postergan_evaluacion, f.total_atraso, f.promocion_guiada, f.desaprobados
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos

        WHERE (anio IN (2024)) AND (LOWER(nombre) LIKE N'%los luceros%' ESCAPE '~' OR cod_mod LIKE N'%los luceros%' ESCAPE '~' OR anexo LIKE N'%los luceros%' ESCAPE '~')
        GROUP BY cod_mod, anexo
        ORDER BY cod_mod, anexo
        
    ;
GO
PRINT 'CASO:ranking_matricula';
SELECT anio, cod_mod, anexo, nombre, nivel_nombre, gestion, COUNT_BIG(*) AS filas, COUNT_BIG(DISTINCT CONCAT(cod_mod, anexo)) AS servicios, SUM(matricula) AS matricula, SUM(cantidad_discapacidad) AS cantidad_discapacidad, SUM(mujeres) AS mujeres, SUM(hombres) AS hombres, SUM(venezolanos) AS venezolanos, SUM(peruanos) AS peruanos, SUM(otros_extranjeros) AS otros_extranjeros, SUM(dni_validado) AS dni_validado, SUM(dni_sin_validar) AS dni_sin_validar, SUM(sin_dni) AS sin_dni, SUM(aprobados) AS aprobados, SUM(retirados) AS retirados, SUM(fallecidos) AS fallecidos, SUM(requieren_recuperacion) AS requieren_recuperacion, SUM(cantidad_situacion_matriculado) AS cantidad_situacion_matriculado, SUM(postergan_evaluacion) AS postergan_evaluacion, SUM(total_atraso) AS total_atraso, CASE WHEN MIN(CASE WHEN promocion_guiada IS NULL THEN 0 ELSE 1 END)=1 THEN SUM(COALESCE(promocion_guiada, 0)) END AS promocion_guiada, CASE WHEN MIN(CASE WHEN desaprobados IS NULL THEN 0 ELSE 1 END)=1 THEN SUM(COALESCE(desaprobados, 0)) END AS desaprobados
FROM (
    SELECT f.anio AS anio, s.cod_mod AS cod_mod, s.anexo AS anexo, s.nombre AS nombre, n.codigo AS nivel, n.descripcion AS nivel_nombre, s.gestion AS gestion, e.edad AS edad, e.rango AS rango_edad, d.tipo AS tipo_discapacidad, f.total_estudiantes AS matricula, f.cantidad_discapacidad, f.mujeres, f.hombres, f.venezolanos, f.peruanos, f.otros_extranjeros, f.dni_validado, f.dni_sin_validar, f.sin_dni, f.aprobados, f.retirados, f.fallecidos, f.requieren_recuperacion, f.cantidad_situacion_matriculado, f.postergan_evaluacion, f.total_atraso, f.promocion_guiada, f.desaprobados
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos

WHERE (anio IN (2024))
GROUP BY anio, cod_mod, anexo, nombre, nivel_nombre, gestion
ORDER BY SUM(matricula) DESC, anio, cod_mod, anexo, nombre, nivel_nombre, gestion
OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY;
GO
PRINT 'CASO:ranking_retiro';
SELECT anio, cod_mod, anexo, nombre, nivel_nombre, gestion, COUNT_BIG(*) AS filas, COUNT_BIG(DISTINCT CONCAT(cod_mod, anexo)) AS servicios, SUM(matricula) AS matricula, SUM(cantidad_discapacidad) AS cantidad_discapacidad, SUM(mujeres) AS mujeres, SUM(hombres) AS hombres, SUM(venezolanos) AS venezolanos, SUM(peruanos) AS peruanos, SUM(otros_extranjeros) AS otros_extranjeros, SUM(dni_validado) AS dni_validado, SUM(dni_sin_validar) AS dni_sin_validar, SUM(sin_dni) AS sin_dni, SUM(aprobados) AS aprobados, SUM(retirados) AS retirados, SUM(fallecidos) AS fallecidos, SUM(requieren_recuperacion) AS requieren_recuperacion, SUM(cantidad_situacion_matriculado) AS cantidad_situacion_matriculado, SUM(postergan_evaluacion) AS postergan_evaluacion, SUM(total_atraso) AS total_atraso, CASE WHEN MIN(CASE WHEN promocion_guiada IS NULL THEN 0 ELSE 1 END)=1 THEN SUM(COALESCE(promocion_guiada, 0)) END AS promocion_guiada, CASE WHEN MIN(CASE WHEN desaprobados IS NULL THEN 0 ELSE 1 END)=1 THEN SUM(COALESCE(desaprobados, 0)) END AS desaprobados
FROM (
    SELECT f.anio AS anio, s.cod_mod AS cod_mod, s.anexo AS anexo, s.nombre AS nombre, n.codigo AS nivel, n.descripcion AS nivel_nombre, s.gestion AS gestion, e.edad AS edad, e.rango AS rango_edad, d.tipo AS tipo_discapacidad, f.total_estudiantes AS matricula, f.cantidad_discapacidad, f.mujeres, f.hombres, f.venezolanos, f.peruanos, f.otros_extranjeros, f.dni_validado, f.dni_sin_validar, f.sin_dni, f.aprobados, f.retirados, f.fallecidos, f.requieren_recuperacion, f.cantidad_situacion_matriculado, f.postergan_evaluacion, f.total_atraso, f.promocion_guiada, f.desaprobados
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos

WHERE (anio IN (2024))
GROUP BY anio, cod_mod, anexo, nombre, nivel_nombre, gestion
HAVING SUM(matricula)>=10
ORDER BY 100.0*SUM(retirados)/NULLIF(SUM(matricula), 0) DESC, anio, cod_mod, anexo, nombre, nivel_nombre, gestion
OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY;
GO
PRINT 'CASO:distribucion_retiro';

        WITH servicios AS (
            SELECT SUM(matricula) AS matricula, SUM(retirados) AS medida
            FROM (
    SELECT f.anio AS anio, s.cod_mod AS cod_mod, s.anexo AS anexo, s.nombre AS nombre, n.codigo AS nivel, n.descripcion AS nivel_nombre, s.gestion AS gestion, e.edad AS edad, e.rango AS rango_edad, d.tipo AS tipo_discapacidad, f.total_estudiantes AS matricula, f.cantidad_discapacidad, f.mujeres, f.hombres, f.venezolanos, f.peruanos, f.otros_extranjeros, f.dni_validado, f.dni_sin_validar, f.sin_dni, f.aprobados, f.retirados, f.fallecidos, f.requieren_recuperacion, f.cantidad_situacion_matriculado, f.postergan_evaluacion, f.total_atraso, f.promocion_guiada, f.desaprobados
    FROM dw.FactMatricula AS f
    JOIN dw.DimServicio AS s ON f.id_servicio=s.id_servicio
    JOIN dw.DimNivel AS n ON f.id_nivel=n.id_nivel
    JOIN dw.DimEdad AS e ON f.id_edad=e.id_edad
    JOIN dw.DimDiscapacidad AS d ON f.id_discapacidad=d.id_discapacidad
) AS datos
 WHERE (anio IN (2024))
            GROUP BY cod_mod, anexo
            HAVING SUM(matricula)>0
        ), tramos AS (
            SELECT CASE WHEN medida=0 THEN 0
                        WHEN 100.0*medida<matricula THEN 1
                        WHEN 100.0*medida<5*matricula THEN 2
                        WHEN 100.0*medida<10*matricula THEN 3
                        WHEN 100.0*medida<50*matricula THEN 4
                        WHEN 100.0*medida<90*matricula THEN 5 ELSE 6 END AS tramo,
                   CASE WHEN matricula<10 THEN 1 ELSE 0 END AS matricula_baja
            FROM servicios
        )
        SELECT tramo, matricula_baja, COUNT(*) AS servicios
        FROM tramos GROUP BY tramo, matricula_baja ORDER BY tramo, matricula_baja
    ;
GO
SET NOCOUNT ON;
PRINT 'LOTES';
SELECT a.anio, RTRIM(l.sha256) AS sha256
FROM dw.DimAnio AS a
JOIN etl.Lote AS l ON l.anio=a.anio AND l.estado='COMPLETADO'
WHERE a.anio BETWEEN 2021 AND 2024
ORDER BY a.anio;

PRINT 'PANEL';
SELECT f.anio, s.cod_mod, s.anexo, n.codigo AS nivel, s.gestion,
       COUNT_BIG(*) AS filas,
       SUM(f.total_estudiantes) AS matricula,
       SUM(f.aprobados) AS aprobados,
       SUM(f.retirados) AS retirados,
       SUM(f.total_atraso) AS total_atraso
FROM dw.FactMatricula AS f
JOIN dw.DimServicio AS s ON s.id_servicio=f.id_servicio AND s.anio=f.anio
JOIN dw.DimNivel AS n ON n.id_nivel=f.id_nivel
WHERE f.anio BETWEEN 2021 AND 2024
GROUP BY f.anio, s.cod_mod, s.anexo, n.codigo, s.gestion
ORDER BY f.anio, s.cod_mod, s.anexo;

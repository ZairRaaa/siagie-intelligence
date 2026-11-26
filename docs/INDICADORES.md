# Indicadores SIAGIE 2021–2024

Los agregados corresponden a registros publicados por servicio, año, nivel, edad y tipo de discapacidad. `FuenteAnalitica.agregados()` acepta filtros por año, nivel, gestión, código modular y anexo, edad y categoría de discapacidad. Devuelve los mismos campos para los dos orígenes. El agrupamiento predeterminado es por año. Usar `por=()` para un total de la selección.

| Indicador | Cálculo | Unidad y alcance |
|---|---|---|
| Matrícula registrada | Suma de `total_estudiantes` en SQL o `TotalEstudiantes` en CSV | Matrículas por periodo. |
| Servicios con registros | Pares distintos de código modular y anexo dentro de la selección | Servicios. Un mismo par puede aparecer en varios años. |
| Variación interanual | 100 × (matrícula actual − matrícula anterior) / matrícula anterior | Porcentaje. Requiere el año inmediatamente anterior con el mismo grupo de filtros. |
| Aprobación y retiro | 100 × suma de aprobados o retirados / matrícula del grupo | Porcentaje de matrículas registradas. |
| Atraso | 100 × suma de `total_atraso` / matrícula del grupo | Porcentaje de matrículas con atraso registrado. |
| Promoción guiada | Suma de `promocion_guiada` y su tasa sobre matrícula | Disponible en 2021 y 2022. |
| Desaprobación | Suma de `desaprobados` y su tasa sobre matrícula | Disponible en 2023 y 2024. |
| Situación final «Matriculado» | Suma de `cantidad_situacion_matriculado` | Conteo de una categoría de la situación final. |
| Características marginales | Sumas de sexo, nacionalidad, DNI y discapacidad registrada | Cada distribución describe una característica. |

Las tasas usan los conteos agregados y se devuelven entre 0 y 100 en las magnitudes anteriores. Se devuelve `None` para una tasa con denominador cero o numerador no disponible. La interfaz podrá mostrarlo como N/D. Cuando se agrega un periodo mixto, las banderas necesitan confirmar disponibilidad en todos los años seleccionados. Si un grupo incluye un valor ausente en una medida con disponibilidad temporal, su total queda ausente. Una selección sin coincidencias devuelve una lista vacía. Una solicitud de años fuera del catálogo devuelve un error explícito.

Los códigos se conservan como texto de siete y tres caracteres. La edad desconocida se representa con `None`. El cero es una edad registrada. La categoría fuente vacía se presenta como «Sin discapacidad registrada» y la categoría publicada «Sin especificacion» conserva su propio valor. Las cifras de sexo, nacionalidad, DNI y situación final son marginales. El análisis no incluye geografía.

## Ejemplo ejecutable

```python
from src.analytics.indicadores import variaciones_anuales
from src.data.contrato import Filtros
from src.data.fuente_analitica import FuenteAnalitica

filtros = Filtros(anios=(2023, 2024), niveles=("B0",))
with FuenteAnalitica("csv") as fuente:
    primaria = variaciones_anuales(fuente.agregados(filtros))
```

Para mantener el mismo alcance al calcular cambios interanuales, pasar a `variaciones_anuales` un único total por año del mismo corte. Si se necesita calcular la variación del primer año mostrado, consultar también el año anterior y filtrar la salida después del cálculo.

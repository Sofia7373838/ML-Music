# `notebooks/` — análisis y experimentos

Los notebooks no tienen lógica propia: importan `src/recommender`, así que lo que se ve aquí
es lo mismo que corre el entrenamiento y la API. Se corren desde esta carpeta (usan rutas
`../data` y `../src`) y en orden.

| Notebook | Entrada | Salida | Qué muestra |
| --- | --- | --- | --- |
| `01_exploracion_datos.ipynb` | `data/raw/dataset.csv` | `data/processed/tracks_clean.csv` | Resumen del dataset, géneros sin macro-género, distribuciones, correlaciones, popularidad, filas con tempo 0 y el resultado de la limpieza |
| `02_modelos.ipynb` | `data/processed/tracks_clean.csv` | — | Codo y silueta para elegir K, composición de los clústeres, comparación de los tres modelos, elección del final y un ejemplo de recomendaciones |

## Cómo correrlos

1. Activa el entorno (`.venv`) y selecciónalo como kernel en VS Code o Jupyter.
2. Descarga `dataset.csv` en `data/raw/` (ver [`data/README.md`](../data/README.md)).
3. Corre `01_exploracion_datos.ipynb` completo.
4. Corre `02_modelos.ipynb` completo. Tarda unos minutos: entrena K-Means para K de 2 a 20.

En SageMaker AI: sube el repositorio a la instancia de notebook, instala
`requirements-dev.txt` en el kernel y descarga el dataset desde S3
(`aws s3 cp s3://<bucket>/data/raw/dataset.csv ../data/raw/`). Apaga la instancia al terminar.

## Hallazgos principales

- La limpieza quita el 28.9 % de las filas (duplicados por género o por varios `track_id`,
  nulos y canciones sin ritmo detectado); quedan 81,061 canciones.
- La silueta es baja para cualquier K (~0.18): el audio cambia de forma continua entre
  estilos y no forma grupos muy separados. Se eligió K = 8.
- Los dos modelos aciertan el macro-género el 32 % de las veces, contra 12 % del azar.
- Las listas tienen muy poca diversidad (0.05 contra 0.94 del azar). Es lo esperado de un
  recomendador por similitud, y es el riesgo de "burbuja de filtro" del análisis ético.
- No hay sesgo de popularidad: lo recomendado tiene en promedio la misma popularidad que la
  canción de entrada.
- Limitación: versiones distintas de la misma canción ("Bohemian Rhapsody" y
  "Bohemian Rhapsody - Remastered 2011") tienen nombre distinto y no se detectan como
  duplicados.

Las salidas de las celdas no se guardan en Git para que los diffs sean legibles; para
capturas del reporte, corre el notebook y exporta las gráficas.

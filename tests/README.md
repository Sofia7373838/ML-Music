# `tests/` — pruebas

Pruebas con pytest. No necesitan el dataset real ni AWS: `conftest.py` arma un catálogo
sintético de 60 canciones en tres grupos con audio muy distinto (rock, clásica y electrónica),
donde un buen modelo debe recomendar canciones del mismo grupo.

```bash
pytest            # todas
pytest -k api     # solo las que tengan "api" en el nombre
pytest -x -q      # parar en la primera falla
```

`pyproject.toml` ya agrega `src` y la raíz al `PYTHONPATH` de pytest.

| Archivo | Qué revisa |
| --- | --- |
| `test_config.py` | Que el modelo no reciba columnas de evaluación (género, popularidad), metadatos ni columnas excluidas |
| `test_genres.py` | Que cada género tenga un solo macro-género y que los desconocidos se marquen |
| `test_data.py` | Limpieza (nulos, tempo 0, duplicados, orden) y **validación de datos**: columnas, nulos, `track_id` repetidos, dataset vacío y rangos |
| `test_features.py` | Que la matriz tenga una columna por variable, media 0 y desviación 1, y que `mode` no se escale |
| `test_models.py` | Que los tres modelos regresen k canciones distintas sin la consultada, respeten el filtro, que kNN ordene por similitud y que el modelo B no salga de su clúster |
| `test_metrics.py` | Cada métrica con casos conocidos y que kNN le gane al azar en el catálogo sintético |
| `test_pipeline.py` | Búsqueda, recomendaciones, `max_popularity`, guardar y cargar el artefacto |
| `test_train.py` | La regla de selección (incluido el desempate por latencia) y el entrenamiento de punta a punta |
| `test_api.py` | Todos los endpoints, errores 404/422 y que cada predicción se registre |
| `test_monitoring.py` | Que el log cumpla el formato EMF y que no tenga datos personales |
| `test_model_store.py` | Lectura de URIs de S3 y carga del modelo desde disco o S3 (S3 simulado) |

El CI corre estas pruebas en cada push y pull request (ver
[`.github/workflows/README.md`](../.github/workflows/README.md)).

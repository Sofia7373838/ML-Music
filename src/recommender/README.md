# `src/recommender` — código del modelo

Todo lo que usan los notebooks, el entrenamiento y la API vive aquí, para que los tres
corran exactamente el mismo código.

## Módulos

| Módulo | Qué hace |
| --- | --- |
| `config.py` | Qué columnas entran al modelo, cuáles solo sirven para evaluar, y los parámetros (`SEED`, `DEFAULT_K`, `N_CLUSTERS`, `PRECISION_TOLERANCE`) |
| `genres.py` | Agrupa los 114 géneros del dataset en 10 macro-géneros para evaluar |
| `data.py` | `load_raw`, `clean`, `load_clean` y `validate` (columnas, nulos, duplicados y rangos) |
| `features.py` | Estandariza las variables continuas y deja `mode` como 0/1 |
| `models.py` | Modelo A, modelo B, referencia al azar y `cluster_scores` (codo y silueta) |
| `metrics.py` | Las métricas de la Tabla 2 y `evaluate` |
| `pipeline.py` | `SongRecommender`: preprocesador + modelo + catálogo. Es el artefacto que usa la API |
| `train.py` | Entrena los tres modelos, los compara, elige uno y guarda el artefacto |

## Flujo

```text
dataset.csv ─load_raw─> clean ─> validate ─> build_preprocessor ─> matriz (n × 10)
                                                                       │
                          ┌────────────────────┬───────────────────────┤
                          ▼                    ▼                       ▼
                     KNNRecommender  ClusterKNNRecommender  RandomRecommender
                          └──────── evaluate (misma muestra) ──────────┘
                                             │
                                    select_model ─> SongRecommender.save()
                                                    models/recommender.joblib
```

## Variables del modelo

Entran 10 variables: `danceability`, `energy`, `speechiness`, `acousticness`,
`instrumentalness`, `liveness`, `valence`, `loudness`, `tempo` (estandarizadas) y `mode` (0/1).

- Se estandarizan porque `tempo` (~120) y `loudness` (~-8 dB) dominarían la similitud frente
  a variables entre 0 y 1.
- `track_genre` y `popularity` **no** entran: se usan para medir precisión y sesgo. Si el
  género entrara, precision@k saldría alta por definición (fuga de información). Hay una
  prueba que lo garantiza (`tests/test_config.py`).
- `key`, `duration_ms` y `time_signature` se excluyen porque no describen cómo suena la canción.

## Modelos

Todos implementan la misma interfaz (`Recommender.recommend(index, k, allowed)`) y nunca
regresan la misma canción que se consultó. `allowed` es una máscara opcional; la API la usa
para el filtro `max_popularity`.

- **A — `KNNRecommender`**: `NearestNeighbors` de scikit-learn con distancia coseno y búsqueda
  exacta (`brute`) sobre las ~81,000 canciones.
- **B — `ClusterKNNRecommender`**: K-Means con K = 8 sobre los vectores normalizados a
  longitud 1 (así la distancia euclidiana de K-Means ordena igual que la coseno) y un
  `NearestNeighbors` por clúster. Cada consulta busca solo dentro del clúster de la canción.
- **Referencia — `RandomRecommender`**: canciones al azar con semilla fija.

K se eligió con `cluster_scores` en `notebooks/02_modelos.ipynb`: la silueta es baja para
cualquier K (~0.18, el audio no forma grupos muy separados) y casi no cambia entre 4 y 8,
mientras que la inercia se aplana alrededor de 8.

## Métricas

| Métrica | Función | Cómo se lee |
| --- | --- | --- |
| Precision@k de género | `genre_precision` | Fracción de las k recomendaciones con el mismo macro-género |
| Diversidad | `intra_list_diversity` | Distancia coseno promedio entre pares de la lista (0 = idénticas) |
| Artistas distintos | `distinct_artists` | Cuántos artistas diferentes hay en la lista |
| Cobertura | `catalog_coverage` | Fracción del catálogo que aparece en alguna lista |
| Sesgo de popularidad | `popularity_gap` | Popularidad promedio recomendada menos la de la entrada |
| Latencia | `evaluate` | p50 y p95 de una llamada a `recommend`, en ms |

La cobertura máxima posible con 2,000 consultas × 10 recomendaciones es 20,000 / 81,061 ≈ 24.7 %,
así que el 21.5 % de los modelos está cerca del tope.

## Elección del modelo final

`select_model` elige el de mayor precision@k. Si otro modelo queda a menos de
`PRECISION_TOLERANCE` (0.01) se consideran empatados y gana el de menor latencia p95.
La referencia al azar nunca puede ganar.

Con los datos actuales A y B empatan (0.3165 contra 0.3160) y B es más rápido, así que se
elige B. Para forzar otro modelo: `python -m recommender.train --model knn`.

## Entrenar

Desde la raíz del repositorio:

```bash
PYTHONPATH=src python -m recommender.train
```

| Opción | Por omisión | Qué es |
| --- | --- | --- |
| `--data` | `data/processed/tracks_clean.csv` | CSV limpio; si no existe, limpia `--raw` |
| `--raw` | `data/raw/dataset.csv` | CSV original de Kaggle |
| `--out` | `models` | Dónde guardar `recommender.joblib` y `metrics.json` |
| `--k` | 10 | Recomendaciones por canción al evaluar |
| `--queries` | 2000 | Canciones de prueba |
| `--clusters` | 8 | K del modelo B |
| `--seed` | 42 | Semilla de K-Means, de la muestra y del azar |
| `--model` | (automático) | `knn`, `cluster_knn` o `random` para forzar uno |

Antes de entrenar se corre `validate`: si hay nulos, `track_id` repetidos o valores fuera de
rango, el entrenamiento se detiene y dice qué columnas fallaron.

## Usar el artefacto desde Python

```python
from recommender.pipeline import SongRecommender

rec = SongRecommender.load("models/recommender.joblib")
song = rec.search("bohemian rhapsody", limit=1)[0]
# Las 10 más parecidas
rec.recommend(song["track_id"], k=10)
# Solo canciones poco populares, para descubrir artistas con poca visibilidad
rec.recommend(song["track_id"], k=10, max_popularity=30)
```

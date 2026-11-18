"""Métricas para comparar los modelos sin usuarios reales (Tabla 2 del avance 1)."""

import time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_distances

from recommender.models import Recommender


def genre_precision(query_genre: str, recommended_genres: pd.Series) -> float:
    """Fracción de recomendaciones con el mismo macro-género que la canción de entrada."""
    if recommended_genres.empty:
        return 0.0
    return float((recommended_genres == query_genre).mean())


def intra_list_diversity(recommended_features: np.ndarray) -> float:
    """Distancia coseno promedio entre cada par de canciones recomendadas."""
    n = len(recommended_features)
    if n < 2:
        return 0.0
    distances = cosine_distances(recommended_features)
    return float(distances[np.triu_indices(n, k=1)].mean())


def distinct_artists(recommended_artists: pd.Series) -> int:
    """Número de artistas distintos en la lista."""
    return int(recommended_artists.nunique())


def popularity_gap(query_popularity: float, recommended_popularity: pd.Series) -> float:
    """Popularidad promedio recomendada menos la de la entrada. Positivo = sesgo a lo popular."""
    if recommended_popularity.empty:
        return 0.0
    return float(recommended_popularity.mean() - query_popularity)


def catalog_coverage(recommended_indices: set[int], n_songs: int) -> float:
    """Fracción del catálogo que apareció en al menos una lista."""
    return len(recommended_indices) / n_songs


def max_appearances(counts: Counter) -> int:
    """Listas en las que aparece la canción más recomendada (detecta *hubs* de kNN)."""
    return max(counts.values(), default=0)


def by_group(rows: pd.DataFrame, tracks: pd.DataFrame, recommended: set[int], k: int) -> dict:
    """Métricas por macro-género de la canción de entrada (mitigación 1 del análisis ético).

    `exposure` es la fracción de canciones de ese macro-género que apareció en al menos una
    lista: si un género queda muy abajo, el sistema casi no lo recomienda.
    """
    exposed = tracks.index.isin(list(recommended))
    exposure = pd.Series(exposed, index=tracks.index).groupby(tracks["macro_genre"]).mean()
    groups = rows.groupby("macro_genre")
    summary = groups[["genre_precision", "diversity", "popularity_gap"]].mean()
    return {
        genre: {
            "queries": int(groups.size()[genre]),
            f"precision@{k}": round(float(summary.at[genre, "genre_precision"]), 4),
            "diversity": round(float(summary.at[genre, "diversity"]), 4),
            "popularity_gap": round(float(summary.at[genre, "popularity_gap"]), 2),
            "exposure": round(float(exposure.get(genre, 0.0)), 4),
        }
        for genre in sorted(summary.index)
    }


def sample_queries(n_songs: int, n_queries: int, seed: int = 42) -> np.ndarray:
    """Índices de las canciones de prueba. Mismo `seed` = misma muestra para cada modelo."""
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n_songs, size=min(n_queries, n_songs), replace=False))


def evaluate(
    model: Recommender,
    tracks: pd.DataFrame,
    features: np.ndarray,
    queries: np.ndarray,
    k: int,
) -> dict[str, float]:
    """Corre el modelo sobre cada canción de `queries` y promedia las métricas."""
    rows = []
    latencies_ms = []
    appearances: Counter = Counter()

    for query in queries:
        start = time.perf_counter()
        recs = model.recommend(int(query), k)
        latencies_ms.append((time.perf_counter() - start) * 1000)

        appearances.update(recs.tolist())
        rec_tracks = tracks.iloc[recs]
        rows.append(
            {
                "macro_genre": tracks["macro_genre"].iat[query],
                "genre_precision": genre_precision(
                    tracks["macro_genre"].iat[query], rec_tracks["macro_genre"]
                ),
                "diversity": intra_list_diversity(features[recs]),
                "distinct_artists": distinct_artists(rec_tracks["artists"]),
                "popularity_gap": popularity_gap(
                    tracks["popularity"].iat[query], rec_tracks["popularity"]
                ),
            }
        )

    rows = pd.DataFrame(rows)
    means = rows.drop(columns="macro_genre").mean()
    recommended = set(appearances)
    return {
        "model": model.name,
        "k": k,
        "queries": len(queries),
        f"precision@{k}": round(float(means["genre_precision"]), 4),
        "diversity": round(float(means["diversity"]), 4),
        "distinct_artists": round(float(means["distinct_artists"]), 2),
        "popularity_gap": round(float(means["popularity_gap"]), 2),
        "coverage": round(catalog_coverage(recommended, len(tracks)), 4),
        "latency_p50_ms": round(float(np.percentile(latencies_ms, 50)), 3),
        "latency_p95_ms": round(float(np.percentile(latencies_ms, 95)), 3),
        "max_appearances": max_appearances(appearances),
        "by_macro_genre": by_group(rows, tracks.reset_index(drop=True), recommended, k),
    }

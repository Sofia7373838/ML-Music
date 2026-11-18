"""Log estructurado por predicción en CloudWatch Embedded Metric Format (EMF).

Cada línea es un JSON que CloudWatch Logs convierte en métricas del namespace
`MusicRecommender` sin llamar a la API de CloudWatch. Solo se registra la canción
consultada, el resultado y el tiempo de respuesta: ningún dato personal.
"""

import json
import sys
import time

NAMESPACE = "MusicRecommender"


def log_prediction(
    *,
    endpoint: str,
    model: str,
    latency_ms: float,
    track_id: str | None = None,
    k: int | None = None,
    found: bool = True,
    max_popularity: int | None = None,
    exclude_explicit: bool = False,
    max_per_artist: int | None = None,
    recommended_ids: list[str] | None = None,
    recommended_popularity: list[int] | None = None,
    recommended_explicit: int = 0,
) -> dict:
    """Escribe un evento en stdout (Lambda lo manda tal cual a CloudWatch) y lo regresa."""
    recommended_ids = recommended_ids or []
    popularity = recommended_popularity or []
    event = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": [["Endpoint"]],
                    "Metrics": [
                        {"Name": "Latency", "Unit": "Milliseconds"},
                        {"Name": "Recommendations", "Unit": "Count"},
                        {"Name": "SongNotFound", "Unit": "Count"},
                        {"Name": "RecommendedPopularity", "Unit": "None"},
                        {"Name": "ExplicitRecommended", "Unit": "Count"},
                    ],
                }
            ],
        },
        "Endpoint": endpoint,
        "Latency": round(latency_ms, 3),
        "Recommendations": len(recommended_ids),
        "SongNotFound": int(not found),
        # EMF acepta una lista de valores: CloudWatch calcula promedio y percentiles.
        "RecommendedPopularity": popularity,
        "ExplicitRecommended": recommended_explicit,
        "model": model,
        "track_id": track_id,
        "k": k,
        "max_popularity": max_popularity,
        "exclude_explicit": exclude_explicit,
        "max_per_artist": max_per_artist,
        "recommended_ids": recommended_ids,
    }
    # print y no logging: el formato por omisión de Lambda antepone texto a cada línea
    # y CloudWatch ya no la reconocería como EMF.
    print(json.dumps(event), file=sys.stdout, flush=True)
    return event

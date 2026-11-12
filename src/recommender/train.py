"""Entrena los tres modelos, los evalúa y guarda el mejor como artefacto.

Uso:
    python -m recommender.train
    python -m recommender.train --data data/processed/tracks_clean.csv --out models
"""

import argparse
import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from recommender.config import DEFAULT_K, EVAL_QUERIES, N_CLUSTERS, PRECISION_TOLERANCE, SEED
from recommender.data import clean, load_clean, load_raw, validate
from recommender.features import build_preprocessor, to_matrix
from recommender.metrics import evaluate, sample_queries
from recommender.models import (
    ClusterKNNRecommender,
    KNNRecommender,
    RandomRecommender,
    build_model,
)
from recommender.pipeline import SongRecommender

MODEL_NAMES = [KNNRecommender.name, ClusterKNNRecommender.name, RandomRecommender.name]
ARTIFACT_NAME = "recommender.joblib"
METRICS_NAME = "metrics.json"


def load_tracks(clean_path: Path, raw_path: Path) -> pd.DataFrame:
    """Usa el CSV limpio si existe; si no, limpia el original."""
    if clean_path.exists():
        return load_clean(clean_path)
    tracks = clean(load_raw(raw_path))
    validate(tracks)
    return tracks


def compare_models(
    tracks: pd.DataFrame, k: int, n_queries: int, n_clusters: int, seed: int
) -> list[dict]:
    """Entrena cada modelo con el mismo preprocesamiento y la misma muestra de prueba."""
    features = to_matrix(build_preprocessor().fit(tracks), tracks)
    queries = sample_queries(len(tracks), n_queries, seed)
    results = []
    for name in MODEL_NAMES:
        model = build_model(name, n_clusters=n_clusters, seed=seed).fit(features)
        results.append(evaluate(model, tracks, features, queries, k))
        print(json.dumps(results[-1]))
    return results


def select_model(results: list[dict], k: int, tolerance: float = PRECISION_TOLERANCE) -> str:
    """Elige el modelo final. La referencia al azar no puede ganar.

    Gana el de mayor precision@k. Si otro queda a menos de `tolerance` de él, se
    consideran empatados y gana el de menor latencia p95.
    """
    metric = f"precision@{k}"
    candidates = [r for r in results if r["model"] != RandomRecommender.name]
    best = max(r[metric] for r in candidates)
    tied = [r for r in candidates if best - r[metric] < tolerance]
    return min(tied, key=lambda r: r["latency_p95_ms"])["model"]


def train(
    clean_path: Path,
    raw_path: Path,
    out_dir: Path,
    k: int = DEFAULT_K,
    n_queries: int = EVAL_QUERIES,
    n_clusters: int = N_CLUSTERS,
    seed: int = SEED,
    model_name: str | None = None,
) -> dict:
    tracks = load_tracks(clean_path, raw_path).reset_index(drop=True)
    results = compare_models(tracks, k, n_queries, n_clusters, seed)
    selected = model_name or select_model(results, k)

    report = {
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "songs": len(tracks),
        "selected_model": selected,
        "n_clusters": n_clusters,
        "seed": seed,
        "versions": {lib: version(lib) for lib in ["scikit-learn", "numpy", "pandas"]},
        "results": results,
    }

    model = build_model(selected, n_clusters=n_clusters, seed=seed)
    recommender = SongRecommender.train(tracks, model, **report)
    recommender.save(out_dir / ARTIFACT_NAME)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / METRICS_NAME).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("data/processed/tracks_clean.csv"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw/dataset.csv"))
    parser.add_argument("--out", type=Path, default=Path("models"))
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--queries", type=int, default=EVAL_QUERIES)
    parser.add_argument("--clusters", type=int, default=N_CLUSTERS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--model", choices=MODEL_NAMES, help="Forzar un modelo en vez de elegir el mejor."
    )
    args = parser.parse_args(argv)

    report = train(
        args.data,
        args.raw,
        args.out,
        k=args.k,
        n_queries=args.queries,
        n_clusters=args.clusters,
        seed=args.seed,
        model_name=args.model,
    )
    print(f"Modelo elegido: {report['selected_model']} -> {args.out / ARTIFACT_NAME}")


if __name__ == "__main__":
    main()

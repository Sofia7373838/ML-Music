import json

import pytest

from recommender.pipeline import SongRecommender
from recommender.train import ARTIFACT_NAME, METRICS_NAME, main, select_model


def result(model, precision, latency):
    return {"model": model, "precision@10": precision, "latency_p95_ms": latency}


def test_select_model_picks_highest_precision():
    results = [result("knn", 0.40, 10), result("cluster_knn", 0.30, 1)]

    assert select_model(results, k=10) == "knn"


def test_select_model_picks_fastest_when_precision_is_tied():
    results = [result("knn", 0.316, 10), result("cluster_knn", 0.312, 1)]

    assert select_model(results, k=10) == "cluster_knn"


def test_select_model_never_picks_random_baseline():
    results = [result("knn", 0.1, 10), result("random", 0.9, 0.01)]

    assert select_model(results, k=10) == "knn"


@pytest.fixture
def trained(tracks, tmp_path):
    data = tmp_path / "tracks_clean.csv"
    tracks.to_csv(data, index=False)
    out = tmp_path / "models"
    main(["--data", str(data), "--out", str(out), "--k", "5", "--queries", "20", "--clusters", "3"])
    return out


def test_train_saves_artifact_and_metrics(trained):
    report = json.loads((trained / METRICS_NAME).read_text(encoding="utf-8"))
    recommender = SongRecommender.load(trained / ARTIFACT_NAME)

    assert {r["model"] for r in report["results"]} == {"knn", "cluster_knn", "random"}
    assert recommender.model_name == report["selected_model"]
    assert recommender.info["songs"] == len(recommender)


def test_train_rejects_invalid_data(tracks, tmp_path):
    data = tmp_path / "tracks_clean.csv"
    tracks.assign(energy=2.0).to_csv(data, index=False)

    with pytest.raises(ValueError, match="energy"):
        main(["--data", str(data), "--out", str(tmp_path / "models")])

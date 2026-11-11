import numpy as np
import pandas as pd
import pytest

from recommender.metrics import (
    catalog_coverage,
    distinct_artists,
    evaluate,
    genre_precision,
    intra_list_diversity,
    popularity_gap,
    sample_queries,
)
from recommender.models import KNNRecommender, RandomRecommender


def test_genre_precision_is_fraction_of_same_genre():
    assert genre_precision("rock", pd.Series(["rock", "pop", "rock", "rock"])) == 0.75


def test_genre_precision_of_empty_list_is_zero():
    assert genre_precision("rock", pd.Series([], dtype=str)) == 0.0


def test_diversity_of_identical_songs_is_zero():
    assert intra_list_diversity(np.ones((3, 4))) == pytest.approx(0.0, abs=1e-6)


def test_diversity_of_orthogonal_songs_is_one():
    assert intra_list_diversity(np.eye(3)) == pytest.approx(1.0)


def test_diversity_of_single_song_is_zero():
    assert intra_list_diversity(np.ones((1, 4))) == 0.0


def test_distinct_artists_counts_unique_names():
    assert distinct_artists(pd.Series(["A", "B", "A"])) == 2


def test_popularity_gap_is_positive_when_recommending_more_popular_songs():
    assert popularity_gap(40, pd.Series([60, 80])) == 30


def test_catalog_coverage():
    assert catalog_coverage({1, 2, 3}, n_songs=12) == 0.25


def test_sample_queries_is_reproducible_and_without_repeats():
    first = sample_queries(100, 20, seed=3)

    np.testing.assert_array_equal(first, sample_queries(100, 20, seed=3))
    assert len(set(first.tolist())) == 20


def test_sample_queries_never_exceeds_catalog():
    assert len(sample_queries(10, 50)) == 10


def test_evaluate_reports_all_metrics(tracks, features):
    queries = sample_queries(len(tracks), 15)

    result = evaluate(KNNRecommender().fit(features), tracks, features, queries, k=5)

    assert result["model"] == "knn"
    assert result["queries"] == 15
    expected = {"precision@5", "diversity", "distinct_artists", "popularity_gap", "coverage"}
    assert expected <= set(result)
    assert result["latency_p95_ms"] >= result["latency_p50_ms"] >= 0


def test_knn_beats_random_baseline_on_separated_groups(tracks, features):
    queries = sample_queries(len(tracks), 30)

    knn = evaluate(KNNRecommender().fit(features), tracks, features, queries, k=5)
    random = evaluate(RandomRecommender().fit(features), tracks, features, queries, k=5)

    assert knn["precision@5"] > random["precision@5"]
    assert knn["diversity"] < random["diversity"]

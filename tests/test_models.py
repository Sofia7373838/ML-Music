import numpy as np
import pytest

from recommender.models import (
    ClusterKNNRecommender,
    KNNRecommender,
    RandomRecommender,
    build_model,
    cluster_scores,
)

ALL_MODELS = [
    KNNRecommender,
    lambda: ClusterKNNRecommender(n_clusters=3),
    RandomRecommender,
]


@pytest.mark.parametrize("make_model", ALL_MODELS)
def test_recommend_returns_k_distinct_songs_without_the_query(features, make_model):
    model = make_model().fit(features)

    recs = model.recommend(0, k=5)

    assert len(recs) == 5
    assert len(set(recs.tolist())) == 5
    assert 0 not in recs


@pytest.mark.parametrize("make_model", ALL_MODELS)
def test_recommend_only_returns_allowed_songs(features, make_model):
    model = make_model().fit(features)
    allowed = np.zeros(len(features), dtype=bool)
    allowed[[3, 7, 15]] = True

    recs = model.recommend(0, k=5, allowed=allowed)

    assert set(recs.tolist()) <= {3, 7, 15}


def test_recommend_returns_fewer_than_k_when_not_enough_songs(features):
    model = KNNRecommender().fit(features)

    assert len(model.recommend(0, k=len(features) + 10)) == len(features) - 1


def test_knn_recommends_songs_from_the_same_group(tracks, features):
    model = KNNRecommender().fit(features)

    recs = model.recommend(0, k=10)

    assert set(tracks["macro_genre"].iloc[recs]) == {tracks["macro_genre"].iat[0]}


def test_knn_orders_by_cosine_similarity(features):
    model = KNNRecommender().fit(features)
    recs = model.recommend(0, k=10)

    unit = features / np.linalg.norm(features, axis=1, keepdims=True)
    similarity = unit[recs] @ unit[0]

    assert np.all(np.diff(similarity) <= 1e-6)


def test_cluster_model_only_recommends_inside_the_query_cluster(features):
    model = ClusterKNNRecommender(n_clusters=3).fit(features)

    recs = model.recommend(0, k=10)

    assert set(model.labels_[recs]) == {model.labels_[0]}
    assert model.pool_size(0) == (model.labels_ == model.labels_[0]).sum()


def test_cluster_model_finds_the_three_groups(tracks, features):
    model = ClusterKNNRecommender(n_clusters=3).fit(features)

    for _, labels in tracks.groupby("macro_genre").groups.items():
        assert len(set(model.labels_[labels])) == 1


def test_random_model_is_reproducible_with_same_seed(features):
    first = RandomRecommender(seed=1).fit(features).recommend(0, k=10)
    second = RandomRecommender(seed=1).fit(features).recommend(0, k=10)

    np.testing.assert_array_equal(first, second)


@pytest.mark.parametrize("name", ["knn", "cluster_knn", "random"])
def test_build_model_by_name(name):
    assert build_model(name, n_clusters=3).name == name


def test_build_model_rejects_unknown_name():
    with pytest.raises(ValueError, match="desconocido"):
        build_model("svm", n_clusters=3)


def test_cluster_scores_has_one_row_per_k(features):
    scores = cluster_scores(features, [2, 3, 4], sample_size=30)

    assert scores["k"].tolist() == [2, 3, 4]
    assert scores["inertia"].is_monotonic_decreasing
    assert scores["silhouette"].between(-1, 1).all()

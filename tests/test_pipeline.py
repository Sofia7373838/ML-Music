import pytest

from recommender.models import ClusterKNNRecommender
from recommender.pipeline import SONG_FIELDS, SongNotFoundError, SongRecommender


def test_find_returns_row_of_track(song_recommender, tracks):
    assert song_recommender.find("rock-03") == tracks.index[tracks["track_id"] == "rock-03"][0]


def test_find_unknown_track_raises(song_recommender):
    with pytest.raises(SongNotFoundError):
        song_recommender.find("no-existe")


def test_song_has_native_python_types(song_recommender):
    song = song_recommender.song(0)

    assert list(song) == SONG_FIELDS
    assert type(song["popularity"]) is int


def test_search_ignores_case_and_matches_artists(song_recommender):
    results = song_recommender.search("CLASICA ARTIST 1")

    assert results
    assert all(song["artists"] == "Clasica Artist 1" for song in results)


def test_search_returns_most_popular_first(song_recommender):
    popularity = [song["popularity"] for song in song_recommender.search("rock", limit=5)]

    assert popularity == sorted(popularity, reverse=True)
    assert len(popularity) == 5


def test_search_with_blank_query_returns_nothing(song_recommender):
    assert song_recommender.search("   ") == []


def test_recommend_returns_songs_with_similarity(song_recommender):
    recs = song_recommender.recommend("rock-00", k=5)

    assert len(recs) == 5
    assert all(rec["track_id"].startswith("rock-") for rec in recs)
    assert all(-1 <= rec["similarity"] <= 1 for rec in recs)
    assert [r["similarity"] for r in recs] == sorted([r["similarity"] for r in recs], reverse=True)


def test_recommend_respects_max_popularity(song_recommender):
    recs = song_recommender.recommend("rock-19", k=5, max_popularity=30)

    assert recs
    assert all(rec["popularity"] <= 30 for rec in recs)


def test_recommend_unknown_track_raises(song_recommender):
    with pytest.raises(SongNotFoundError):
        song_recommender.recommend("no-existe")


def test_save_and_load_keep_recommendations(song_recommender, tmp_path):
    path = song_recommender.save(tmp_path / "nested" / "model.joblib")

    loaded = SongRecommender.load(path)

    assert loaded.recommend("rock-00") == song_recommender.recommend("rock-00")
    assert loaded.info == song_recommender.info


def test_load_rejects_other_objects(tmp_path):
    import joblib

    path = tmp_path / "other.joblib"
    joblib.dump({"not": "a model"}, path)

    with pytest.raises(TypeError):
        SongRecommender.load(path)


def test_train_works_with_cluster_model(tracks):
    recommender = SongRecommender.train(tracks, ClusterKNNRecommender(n_clusters=3))

    assert recommender.model_name == "cluster_knn"
    assert len(recommender.recommend("electronica-04", k=3)) == 3

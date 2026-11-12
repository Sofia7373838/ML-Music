import pytest

from api import model_store
from api.model_store import get_recommender, parse_s3_uri


def test_parse_s3_uri():
    assert parse_s3_uri("s3://bucket/models/model.joblib") == ("bucket", "models/model.joblib")


@pytest.mark.parametrize("uri", ["bucket/model.joblib", "s3://bucket", "s3:///model.joblib"])
def test_parse_s3_uri_rejects_invalid(uri):
    with pytest.raises(ValueError):
        parse_s3_uri(uri)


@pytest.fixture(autouse=True)
def clear_cache():
    get_recommender.cache_clear()
    yield
    get_recommender.cache_clear()


def test_loads_local_model_from_model_path(song_recommender, tmp_path, monkeypatch):
    path = song_recommender.save(tmp_path / "model.joblib")
    monkeypatch.delenv("MODEL_S3_URI", raising=False)
    monkeypatch.setenv("MODEL_PATH", str(path))

    assert len(get_recommender()) == len(song_recommender)


def test_loads_model_from_s3_when_uri_is_set(song_recommender, tmp_path, monkeypatch):
    path = song_recommender.save(tmp_path / "model.joblib")
    calls = []

    def fake_download(uri):
        calls.append(uri)
        return path

    monkeypatch.setenv("MODEL_S3_URI", "s3://bucket/models/model.joblib")
    monkeypatch.setattr(model_store, "download_from_s3", fake_download)

    assert len(get_recommender()) == len(song_recommender)
    assert calls == ["s3://bucket/models/model.joblib"]


def test_model_is_loaded_once(song_recommender, tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_S3_URI", raising=False)
    monkeypatch.setenv("MODEL_PATH", str(song_recommender.save(tmp_path / "model.joblib")))

    assert get_recommender() is get_recommender()

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.model_store import get_recommender


@pytest.fixture
def client(song_recommender):
    app.dependency_overrides[get_recommender] = lambda: song_recommender
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_index_serves_the_web_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Music Recommender</title>" in response.text


def test_index_answers_head_requests(client):
    # Algunas herramientas de monitoreo revisan si la página existe con HEAD.
    assert client.head("/").status_code == 200


def test_index_does_not_need_the_model():
    # Sin dependency_overrides: si la ruta pidiera el modelo, intentaría cargarlo de disco.
    assert TestClient(app).get("/").status_code == 200


def test_index_is_not_in_the_api_docs(client):
    assert "/" not in client.get("/openapi.json").json()["paths"]


def test_health(client):
    body = client.get("/health").json()

    assert body == {
        "status": "ok",
        "model": "knn",
        "songs": 60,
        "trained_at": "2026-11-10T00:00:00+00:00",
    }


def test_search(client):
    response = client.get("/songs/search", params={"q": "rock", "limit": 3})

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_search_requires_two_characters(client):
    assert client.get("/songs/search", params={"q": "r"}).status_code == 422


def test_get_song(client):
    assert client.get("/songs/rock-01").json()["track_name"] == "Rock Song 1"


def test_get_unknown_song_returns_404(client):
    assert client.get("/songs/no-existe").status_code == 404


def test_recommendations(client):
    response = client.post("/recommendations", json={"track_id": "clasica-02", "k": 4})

    body = response.json()
    assert response.status_code == 200
    assert body["model"] == "knn"
    assert body["query"]["track_id"] == "clasica-02"
    assert len(body["recommendations"]) == 4
    assert all("similarity" in rec for rec in body["recommendations"])
    assert all(rec["reason"] for rec in body["recommendations"])


def test_recommendations_with_max_popularity(client):
    response = client.post(
        "/recommendations", json={"track_id": "rock-19", "k": 3, "max_popularity": 20}
    )

    assert all(rec["popularity"] <= 20 for rec in response.json()["recommendations"])


def test_recommendations_can_exclude_explicit_songs(client):
    response = client.post(
        "/recommendations", json={"track_id": "rock-01", "k": 10, "exclude_explicit": True}
    )

    assert not any(rec["explicit"] for rec in response.json()["recommendations"])


def test_recommendations_cap_songs_per_artist_by_default(client):
    response = client.post("/recommendations", json={"track_id": "rock-01", "k": 10})

    artists = [rec["artists"] for rec in response.json()["recommendations"]]
    assert max(artists.count(artist) for artist in artists) <= 2


def test_recommendations_without_artist_cap(client):
    response = client.post(
        "/recommendations", json={"track_id": "rock-01", "k": 19, "max_per_artist": None}
    )

    assert len(response.json()["recommendations"]) == 19


@pytest.mark.parametrize(
    "payload",
    [{"track_id": "rock-01", "k": 0}, {"k": 5}, {"track_id": "rock-01", "max_per_artist": 0}],
)
def test_recommendations_validates_request(client, payload):
    assert client.post("/recommendations", json=payload).status_code == 422


def test_recommendations_logs_each_prediction(client, capsys):
    client.post("/recommendations", json={"track_id": "rock-01", "k": 2})

    event = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert event["track_id"] == "rock-01"
    assert event["Recommendations"] == 2
    assert event["SongNotFound"] == 0
    assert len(event["recommended_ids"]) == 2
    assert len(event["RecommendedPopularity"]) == 2


def test_unknown_song_returns_404_and_is_logged(client, capsys):
    response = client.post("/recommendations", json={"track_id": "no-existe"})

    event = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert response.status_code == 404
    assert event["SongNotFound"] == 1

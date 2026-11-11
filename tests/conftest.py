import numpy as np
import pandas as pd
import pytest

from recommender.config import MODEL_FEATURES
from recommender.features import build_preprocessor, to_matrix
from recommender.models import KNNRecommender
from recommender.pipeline import SongRecommender

# Tres grupos con perfiles de audio muy distintos: un buen modelo debe recomendar
# canciones del mismo grupo.
PROFILES = {
    "rock": {"energy": 0.9, "loudness": -4.0, "acousticness": 0.05, "tempo": 150.0},
    "clasica": {"energy": 0.1, "loudness": -25.0, "acousticness": 0.95, "tempo": 70.0},
    "electronica": {"danceability": 0.9, "instrumentalness": 0.9, "tempo": 125.0},
}


def make_tracks(per_group: int = 20, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for genre, profile in PROFILES.items():
        for i in range(per_group):
            row = {
                feature: float(np.clip(0.5 + rng.normal(0, 0.03), 0, 1))
                for feature in MODEL_FEATURES
            }
            row.update({name: value + rng.normal(0, 0.01) for name, value in profile.items()})
            row.update(
                track_id=f"{genre}-{i:02d}",
                track_name=f"{genre.title()} Song {i}",
                artists=f"{genre.title()} Artist {i % 5}",
                album_name="Album",
                track_genre=genre,
                macro_genre=genre,
                popularity=int(i * 100 / (per_group - 1)),
                mode=i % 2,
            )
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def tracks() -> pd.DataFrame:
    return make_tracks()


@pytest.fixture
def features(tracks) -> np.ndarray:
    return to_matrix(build_preprocessor().fit(tracks), tracks)


@pytest.fixture
def song_recommender(tracks) -> SongRecommender:
    return SongRecommender.train(tracks, KNNRecommender(), trained_at="2026-11-10T00:00:00+00:00")

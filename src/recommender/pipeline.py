"""Une preprocesador, modelo y catálogo en el artefacto que se guarda en S3 y usa la API."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer

from recommender.config import METADATA_COLUMNS, MODEL_FEATURES
from recommender.features import build_preprocessor, to_matrix
from recommender.models import Recommender

CATALOG_COLUMNS = METADATA_COLUMNS + ["track_genre", "macro_genre", "popularity"]
SONG_FIELDS = ["track_id", "track_name", "artists", "album_name", "track_genre", "popularity"]


class SongNotFoundError(KeyError):
    """El `track_id` no está en el catálogo."""


@dataclass
class SongRecommender:
    preprocessor: ColumnTransformer
    model: Recommender
    catalog: pd.DataFrame
    info: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._index = {track_id: i for i, track_id in enumerate(self.catalog["track_id"])}

    @classmethod
    def train(cls, tracks: pd.DataFrame, model: Recommender, **info: Any) -> Self:
        """Ajusta el preprocesador y el modelo con todo el catálogo."""
        tracks = tracks.reset_index(drop=True)
        preprocessor = build_preprocessor().fit(tracks[MODEL_FEATURES])
        model.fit(to_matrix(preprocessor, tracks))
        return cls(preprocessor, model, tracks[CATALOG_COLUMNS].copy(), dict(info))

    @property
    def model_name(self) -> str:
        return self.model.name

    def __len__(self) -> int:
        return len(self.catalog)

    def song(self, index: int) -> dict[str, Any]:
        row = self.catalog.iloc[index]
        return {name: _to_python(row[name]) for name in SONG_FIELDS}

    def find(self, track_id: str) -> int:
        try:
            return self._index[track_id]
        except KeyError:
            raise SongNotFoundError(track_id) from None

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca por nombre o artista (sin distinguir mayúsculas), las más populares primero."""
        query = query.strip().casefold()
        if not query:
            return []
        names = self.catalog["track_name"].str.casefold()
        artists = self.catalog["artists"].str.casefold()
        hits = self.catalog[
            names.str.contains(query, regex=False) | artists.str.contains(query, regex=False)
        ]
        top = hits.sort_values(["popularity", "track_id"], ascending=[False, True]).head(limit)
        return [self.song(self._index[track_id]) for track_id in top["track_id"]]

    def recommend(
        self, track_id: str, k: int = 10, max_popularity: int | None = None
    ) -> list[dict[str, Any]]:
        """Regresa `k` canciones parecidas a `track_id` con su similitud coseno.

        `max_popularity` limita las recomendaciones a canciones con esa popularidad o
        menos, para descubrir artistas con poca visibilidad.
        """
        index = self.find(track_id)
        allowed = None
        if max_popularity is not None:
            allowed = (self.catalog["popularity"] <= max_popularity).to_numpy()

        recs = self.model.recommend(index, k, allowed=allowed)
        similarity = _cosine_similarity(self.model.features[index], self.model.features[recs])
        return [
            {**self.song(rec), "similarity": round(float(sim), 4)}
            for rec, sim in zip(recs, similarity, strict=True)
        ]

    def _allowed(self, max_popularity: int | None, exclude_explicit: bool) -> np.ndarray | None:
        """Máscara de canciones que se pueden recomendar, o None si no hay filtros."""
        if max_popularity is None and not exclude_explicit:
            return None
        allowed = np.ones(len(self), dtype=bool)
        if max_popularity is not None:
            allowed &= (self.catalog["popularity"] <= max_popularity).to_numpy()
        if exclude_explicit:
            allowed &= ~self.catalog["explicit"].to_numpy(dtype=bool)
        return allowed

    def _select(
        self, index: int, k: int, allowed: np.ndarray | None, max_per_artist: int | None
        ) -> np.ndarray:
        """Pide candidatos al modelo y aplica el tope por artista, conservando el orden."""
        if max_per_artist is None:
            return self.model.recommend(index, k, allowed=allowed)
        n = k
        while True:
            candidates = self.model.recommend(index, n, allowed=allowed)
            picked = self._cap_per_artist(candidates, k, max_per_artist)
            if len(picked) >= k or len(candidates) < n:
                return picked
            n *= 4

    def _cap_per_artist(self, candidates: np.ndarray, k: int, max_per_artist: int) -> np.ndarray:
        counts: dict[str, int] = {}
        picked = []
        for candidate in candidates:
            artists = _split_artists(self.catalog["artists"].iat[candidate])
            if any(counts.get(artist, 0) >= max_per_artist for artist in artists):
                continue
            for artist in artists:
                counts[artist] = counts.get(artist, 0) + 1
            picked.append(candidate)
            if len(picked) == k:
                break
        return np.asarray(picked, dtype=int)


    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)
        return path

    @classmethod
    def load(cls, path: str | Path) -> Self:
        recommender = joblib.load(path)
        if not isinstance(recommender, cls):
            raise TypeError(f"{path} no contiene un SongRecommender")
        return recommender


def _cosine_similarity(query: np.ndarray, others: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(others, axis=1) * np.linalg.norm(query)
    return np.divide(others @ query, norms, out=np.zeros(len(others)), where=norms > 0)

def _split_artists(artists: str) -> list[str]:
    """El dataset separa a los artistas con `;`."""
    return [artist.strip().casefold() for artist in artists.split(";") if artist.strip()]



def _to_python(value: Any) -> Any:
    """Convierte tipos de numpy a tipos nativos para que FastAPI los serialice."""
    return value.item() if isinstance(value, np.generic) else value

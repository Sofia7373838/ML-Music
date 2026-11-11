"""Modelos de recomendación: kNN (A), K-Means + kNN (B) y recomendaciones al azar.

Todos trabajan sobre la matriz de `features.to_matrix` y regresan índices de filas del
catálogo. Ninguno recibe el género, que se reserva para evaluar.
"""

from abc import ABC, abstractmethod
from typing import Self

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize


class Recommender(ABC):
    """Interfaz común. Las subclases solo definen cómo ordenar los candidatos."""

    name = ""

    def fit(self, features: np.ndarray) -> Self:
        self._features = features
        self._fit(features)
        return self

    @property
    def features(self) -> np.ndarray:
        return self._features

    @property
    def n_songs(self) -> int:
        return len(self._features)

    def recommend(self, index: int, k: int, allowed: np.ndarray | None = None) -> np.ndarray:
        """Regresa hasta `k` índices de canciones parecidas a `index`, sin incluirla.

        `allowed` es una máscara booleana opcional sobre el catálogo (por ejemplo, solo
        canciones poco populares). Se piden más candidatos hasta juntar `k` permitidos o
        agotar las canciones que el modelo puede regresar.
        """
        pool = self.pool_size(index)
        n = k + 1
        while True:
            candidates = self._candidates(index, min(n, pool))
            candidates = candidates[candidates != index]
            if allowed is not None:
                candidates = candidates[allowed[candidates]]
            if len(candidates) >= k or n >= pool:
                return candidates[:k]
            n *= 4

    def pool_size(self, index: int) -> int:
        """Número de canciones entre las que el modelo busca para `index`."""
        return self.n_songs

    @abstractmethod
    def _fit(self, features: np.ndarray) -> None: ...

    @abstractmethod
    def _candidates(self, index: int, n: int) -> np.ndarray:
        """Regresa `n` índices ordenados del más al menos parecido (puede incluir `index`)."""


class KNNRecommender(Recommender):
    """Modelo A: los vecinos más cercanos por similitud coseno en todo el catálogo."""

    name = "knn"

    def _fit(self, features: np.ndarray) -> None:
        self._nn = NearestNeighbors(metric="cosine", algorithm="brute").fit(features)

    def _candidates(self, index: int, n: int) -> np.ndarray:
        query = self._features[index : index + 1]
        return self._nn.kneighbors(query, n_neighbors=n, return_distance=False)[0]


class ClusterKNNRecommender(Recommender):
    """Modelo B: agrupa con K-Means y busca vecinos solo dentro del clúster de la canción.

    K-Means usa distancia euclidiana, así que se entrena sobre vectores normalizados a
    longitud 1: en ese espacio la distancia euclidiana ordena igual que la coseno.
    """

    name = "cluster_knn"

    def __init__(self, n_clusters: int, seed: int = 42):
        self.n_clusters = n_clusters
        self.seed = seed

    def _fit(self, features: np.ndarray) -> None:
        self.kmeans = KMeans(n_clusters=self.n_clusters, n_init=10, random_state=self.seed)
        self.labels_ = self.kmeans.fit_predict(normalize(features))
        self._members = [np.flatnonzero(self.labels_ == c) for c in range(self.n_clusters)]
        self._nns = [
            NearestNeighbors(metric="cosine", algorithm="brute").fit(features[members])
            for members in self._members
        ]

    def pool_size(self, index: int) -> int:
        return len(self._members[self.labels_[index]])

    def _candidates(self, index: int, n: int) -> np.ndarray:
        cluster = self.labels_[index]
        query = self._features[index : index + 1]
        local = self._nns[cluster].kneighbors(query, n_neighbors=n, return_distance=False)[0]
        return self._members[cluster][local]


class RandomRecommender(Recommender):
    """Referencia: canciones al azar. Sirve para saber si los modelos aportan algo."""

    name = "random"

    def __init__(self, seed: int = 42):
        self.seed = seed

    def _fit(self, features: np.ndarray) -> None:
        self._rng = np.random.default_rng(self.seed)

    def _candidates(self, index: int, n: int) -> np.ndarray:
        return self._rng.choice(self.n_songs, size=n, replace=False)


def build_model(name: str, n_clusters: int, seed: int = 42) -> Recommender:
    """Crea un modelo sin entrenar a partir de su nombre."""
    if name == KNNRecommender.name:
        return KNNRecommender()
    if name == ClusterKNNRecommender.name:
        return ClusterKNNRecommender(n_clusters=n_clusters, seed=seed)
    if name == RandomRecommender.name:
        return RandomRecommender(seed=seed)
    raise ValueError(f"Modelo desconocido: {name}")


def cluster_scores(
    features: np.ndarray, ks: list[int], sample_size: int = 10_000, seed: int = 42
) -> pd.DataFrame:
    """Inercia (método del codo) y coeficiente de silueta para cada K.

    La silueta cuesta O(n²), así que se calcula sobre una muestra de `sample_size`.
    """
    unit = normalize(features)
    rows = []
    for k in ks:
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(unit)
        silhouette = silhouette_score(
            unit, kmeans.labels_, sample_size=min(sample_size, len(unit)), random_state=seed
        )
        rows.append({"k": k, "inertia": kmeans.inertia_, "silhouette": silhouette})
    return pd.DataFrame(rows)

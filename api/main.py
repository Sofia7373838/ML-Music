"""API REST del recomendador. En local: `uvicorn api.main:app --reload`."""

import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from api.model_store import get_recommender
from api.monitoring import log_prediction
from recommender.config import MAX_PER_ARTIST
from recommender.pipeline import SongNotFoundError, SongRecommender

app = FastAPI(
    title="Music Recommender",
    description="Dada una canción, regresa las más parecidas según sus características de audio.",
    version="1.0.0",
)

Recommender = Annotated[SongRecommender, Depends(get_recommender)]


class Song(BaseModel):
    track_id: str
    track_name: str
    artists: str
    album_name: str
    track_genre: str
    popularity: int
    explicit: bool


class RecommendedSong(Song):
    similarity: float = Field(description="Similitud coseno con la canción de entrada (-1 a 1).")
    reason: str = Field(
        description="Rasgos de audio que comparte con la canción de entrada.",
        examples=["Comparten: mucha energía y tempo rápido"],
    )


class RecommendationRequest(BaseModel):
    track_id: str = Field(examples=["5SuOikwiRyPMVoIQDJUgSV"])
    k: int = Field(default=10, ge=1, le=50)
    max_popularity: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Solo recomendar canciones con esta popularidad o menos.",
    )
    exclude_explicit: bool = Field(
        default=False, description="Quitar canciones con contenido explícito."
    )
    max_per_artist: int | None = Field(
        default=MAX_PER_ARTIST,
        ge=1,
        le=50,
        description="Máximo de canciones de un mismo artista en la lista. `null` = sin tope.",
    )


class RecommendationResponse(BaseModel):
    model: str
    query: Song
    recommendations: list[RecommendedSong]


class Health(BaseModel):
    status: str
    model: str
    songs: int
    trained_at: str | None


@app.get("/health")
def health(recommender: Recommender) -> Health:
    return Health(
        status="ok",
        model=recommender.model_name,
        songs=len(recommender),
        trained_at=recommender.info.get("trained_at"),
    )


@app.get("/songs/search")
def search_songs(
    recommender: Recommender,
    q: Annotated[str, Query(min_length=2, description="Nombre de la canción o artista")],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[Song]:
    return recommender.search(q, limit)


@app.get("/songs/{track_id}")
def get_song(recommender: Recommender, track_id: str) -> Song:
    try:
        return recommender.song(recommender.find(track_id))
    except SongNotFoundError:
        raise HTTPException(404, f"No existe la canción {track_id}") from None


@app.post("/recommendations")
def recommend(recommender: Recommender, request: RecommendationRequest) -> RecommendationResponse:
    start = time.perf_counter()
    try:
        query = recommender.song(recommender.find(request.track_id))
        recs = recommender.recommend(
            request.track_id,
            request.k,
            max_popularity=request.max_popularity,
            exclude_explicit=request.exclude_explicit,
            max_per_artist=request.max_per_artist,
        )
    except SongNotFoundError:
        _log(recommender, request, start, recs=[], found=False)
        raise HTTPException(404, f"No existe la canción {request.track_id}") from None

    _log(recommender, request, start, recs=recs, found=True)
    return RecommendationResponse(model=recommender.model_name, query=query, recommendations=recs)


def _log(
    recommender: SongRecommender,
    request: RecommendationRequest,
    start: float,
    recs: list[dict],
    found: bool,
) -> None:
    log_prediction(
        endpoint="recommendations",
        model=recommender.model_name,
        latency_ms=(time.perf_counter() - start) * 1000,
        track_id=request.track_id,
        k=request.k,
        found=found,
        max_popularity=request.max_popularity,
        exclude_explicit=request.exclude_explicit,
        max_per_artist=request.max_per_artist,
        recommended_ids=[rec["track_id"] for rec in recs],
        recommended_popularity=[rec["popularity"] for rec in recs],
        recommended_explicit=sum(rec["explicit"] for rec in recs),
    )

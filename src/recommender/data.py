"""Carga y limpieza del Spotify Tracks Dataset."""

from pathlib import Path

import pandas as pd

from recommender.config import EVALUATION_COLUMNS, METADATA_COLUMNS, MODEL_FEATURES
from recommender.genres import to_macro_genre

REQUIRED_COLUMNS = METADATA_COLUMNS + MODEL_FEATURES + EVALUATION_COLUMNS


def load_raw(path: str | Path) -> pd.DataFrame:
    """Lee el CSV original y revisa que tenga las columnas necesarias."""
    df = pd.read_csv(path, index_col=0)
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Faltan columnas en el dataset: {missing}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Quita nulos, canciones sin ritmo detectado y duplicados, y agrega `macro_genre`.

    Un `tempo` de 0 no es un valor real: indica que no se detectó ritmo, como en el
    ruido blanco. La columna se conserva; solo se quitan esas filas.

    La misma canción puede aparecer con varios `track_id` o en varios géneros, así que
    queda una fila por nombre + artistas: la más popular. Su `macro_genre` es el más
    frecuente entre todas sus apariciones, para no depender del orden del CSV.
    """
    tracks = df[REQUIRED_COLUMNS].dropna()
    tracks = tracks[tracks["tempo"] > 0].copy()
    tracks["macro_genre"] = tracks["track_genre"].map(to_macro_genre)

    key = ["_name", "_artists"]
    tracks["_name"] = tracks["track_name"].str.strip().str.casefold()
    tracks["_artists"] = tracks["artists"].str.strip().str.casefold()

    macro_by_song = (
        tracks.groupby(key)["macro_genre"].agg(lambda genres: genres.mode().iloc[0]).reset_index()
    )
    best_rows = (
        tracks.drop(columns="macro_genre")
        .sort_values(["popularity", "track_id"], ascending=[False, True])
        .drop_duplicates(key)
    )
    return (
        best_rows.merge(macro_by_song, on=key)
        .drop(columns=key)
        .sort_values("track_id")
        .reset_index(drop=True)
    )
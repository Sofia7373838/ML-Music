"""Carga el modelo una sola vez por contenedor, desde S3 o desde un archivo local.

Variables de entorno:
    MODEL_S3_URI  s3://bucket/ruta/recommender.joblib (en Lambda)
    MODEL_PATH    ruta local; por omisión models/recommender.joblib
"""

import os
import tempfile
from functools import cache
from pathlib import Path

from recommender.pipeline import SongRecommender

DEFAULT_MODEL_PATH = "models/recommender.joblib"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Separa `s3://bucket/llave` en (bucket, llave)."""
    if not uri.startswith("s3://"):
        raise ValueError(f"URI de S3 inválida: {uri}")
    bucket, _, key = uri.removeprefix("s3://").partition("/")
    if not bucket or not key:
        raise ValueError(f"URI de S3 inválida: {uri}")
    return bucket, key


def download_from_s3(uri: str) -> Path:
    """Descarga el artefacto a /tmp, el único directorio con escritura en Lambda."""
    import boto3

    bucket, key = parse_s3_uri(uri)
    target = Path(tempfile.gettempdir()) / Path(key).name
    boto3.client("s3").download_file(bucket, key, str(target))
    return target


@cache
def get_recommender() -> SongRecommender:
    uri = os.environ.get("MODEL_S3_URI")
    path = download_from_s3(uri) if uri else Path(os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH))
    return SongRecommender.load(path)

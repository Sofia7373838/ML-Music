"""Columnas del dataset y el papel de cada una en el proyecto."""

SCALED_FEATURES = [
    "danceability",
    "energy",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "loudness",
    "tempo",
]
BINARY_FEATURES = ["mode"]
MODEL_FEATURES = SCALED_FEATURES + BINARY_FEATURES

# El género y la popularidad solo se usan para evaluar. Si el género entrara al
# modelo, precision@k saldría alta por definición (fuga de información).
EVALUATION_COLUMNS = ["track_genre", "popularity"]

METADATA_COLUMNS = ["track_id", "track_name", "artists", "album_name"]

# Solo se usan para filtrar lo que regresa la API (por ejemplo, `exclude_explicit`).
FILTER_COLUMNS = ["explicit"]

# key es categórica; duration_ms y time_signature no describen cómo suena la canción.
EXCLUDED_COLUMNS = ["key", "duration_ms", "time_signature"]

# Entrenamiento y evaluación.
SEED = 42
DEFAULT_K = 10
EVAL_QUERIES = 2_000
# K del modelo B, elegido con el codo y la silueta en notebooks/02_modelos.ipynb.
N_CLUSTERS = 8
# Diferencia de precision@k por debajo de la cual dos modelos se consideran empatados
# y se elige el más rápido.
PRECISION_TOLERANCE = 0.01

# Mitigaciones del análisis ético (sección 9.4 del avance 1).
# Máximo de canciones del mismo artista en una lista de la API.
MAX_PER_ARTIST = 2

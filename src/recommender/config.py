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

# key es categórica; duration_ms y time_signature no describen cómo suena la canción.
EXCLUDED_COLUMNS = ["key", "duration_ms", "time_signature"]
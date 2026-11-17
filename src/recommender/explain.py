"""Explica en palabras por qué se recomendó una canción.

Trabaja sobre la matriz estandarizada de `features.to_matrix`: un valor positivo en una
variable significa "más que la canción promedio del catálogo" y uno negativo "menos".
Una característica se considera compartida cuando las dos canciones se alejan del promedio
en la misma dirección; se reportan las que comparten con más fuerza.
"""

import numpy as np

from recommender.config import SCALED_FEATURES

# (descripción si está arriba del promedio, descripción si está abajo)
FEATURE_LABELS = {
    "danceability": ("muy bailable", "poco bailable"),
    "energy": ("mucha energía", "poca energía"),
    "speechiness": ("mucha voz hablada", "poca voz hablada"),
    "acousticness": ("sonido acústico", "sonido poco acústico"),
    "instrumentalness": ("instrumental", "con voz"),
    "liveness": ("sonido en vivo", "sonido de estudio"),
    "valence": ("tono alegre", "tono melancólico"),
    "loudness": ("volumen alto", "volumen bajo"),
    "tempo": ("tempo rápido", "tempo lento"),
}

# Media desviación estándar: por debajo de eso la variable es "normal" y no la describe.
MIN_SHARED = 0.5
GENERAL_REASON = "perfil de audio parecido en general"


def shared_traits(query: np.ndarray, other: np.ndarray, top: int = 2) -> list[str]:
    """Hasta `top` rasgos que comparten dos canciones, del más al menos marcado.

    `query` y `other` son filas de la matriz estandarizada; solo se miran las columnas de
    `SCALED_FEATURES` (las primeras), no `mode`.
    """
    n = len(SCALED_FEATURES)
    q, o = query[:n], other[:n]
    same_side = np.sign(q) == np.sign(o)
    strength = np.where(same_side, np.minimum(np.abs(q), np.abs(o)), 0.0)

    traits = []
    for j in np.argsort(-strength, kind="stable")[:top]:
        if strength[j] < MIN_SHARED:
            break
        high, low = FEATURE_LABELS[SCALED_FEATURES[j]]
        traits.append(high if q[j] > 0 else low)
    return traits


def explain(query: np.ndarray, other: np.ndarray, top: int = 2) -> str:
    """Frase corta para la API, por ejemplo "Comparten: mucha energía y tempo rápido"."""
    traits = shared_traits(query, other, top)
    if not traits:
        return GENERAL_REASON.capitalize()
    return "Comparten: " + " y ".join(traits)

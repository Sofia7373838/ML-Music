"""Convierte las columnas de audio en la matriz numérica que reciben los modelos."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

from recommender.config import BINARY_FEATURES, MODEL_FEATURES, SCALED_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """Estandariza las variables continuas y deja `mode` como 0/1.

    Sin estandarizar, `tempo` (~120) y `loudness` (~-8) dominarían la similitud frente a
    variables entre 0 y 1 como `energy`.
    """
    return ColumnTransformer(
        [
            ("scaled", StandardScaler(), SCALED_FEATURES),  # 9 columnas: se estandarizan
            ("binary", "passthrough", BINARY_FEATURES),  # mode (0 o 1): se deja igual
        ],
        verbose_feature_names_out=False,
    )


def to_matrix(preprocessor: ColumnTransformer, tracks: pd.DataFrame) -> np.ndarray:
    """Aplica un preprocesador ya ajustado y regresa un arreglo float32."""
    return np.asarray(preprocessor.transform(tracks[MODEL_FEATURES]), dtype=np.float32)

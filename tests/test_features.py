import numpy as np
import pytest

from recommender.config import BINARY_FEATURES, MODEL_FEATURES, SCALED_FEATURES


def test_matrix_has_one_column_per_model_feature(tracks, features):
    assert features.shape == (len(tracks), len(MODEL_FEATURES))
    assert features.dtype == np.float32


def test_scaled_features_have_zero_mean_and_unit_std(features):
    scaled = features[:, : len(SCALED_FEATURES)]

    assert scaled.mean(axis=0) == pytest.approx(0, abs=1e-5)
    assert scaled.std(axis=0) == pytest.approx(1, abs=1e-3)


def test_binary_features_are_not_scaled(tracks, features):
    binary = features[:, len(SCALED_FEATURES) :]

    np.testing.assert_array_equal(binary, tracks[BINARY_FEATURES].to_numpy())

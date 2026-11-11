from recommender.config import (
    BINARY_FEATURES,
    EVALUATION_COLUMNS,
    EXCLUDED_COLUMNS,
    METADATA_COLUMNS,
    MODEL_FEATURES,
    SCALED_FEATURES,
)


def test_model_features_are_scaled_plus_binary():
    assert MODEL_FEATURES == SCALED_FEATURES + BINARY_FEATURES
    assert len(MODEL_FEATURES) == len(set(MODEL_FEATURES))


def test_model_does_not_receive_evaluation_columns():
    assert not set(MODEL_FEATURES) & set(EVALUATION_COLUMNS)


def test_model_does_not_receive_excluded_or_metadata_columns():
    assert not set(MODEL_FEATURES) & set(EXCLUDED_COLUMNS)
    assert not set(MODEL_FEATURES) & set(METADATA_COLUMNS)

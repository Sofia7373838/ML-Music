import numpy as np

from recommender.config import SCALED_FEATURES
from recommender.explain import GENERAL_REASON, explain, shared_traits


def vector(**values):
    row = np.zeros(len(SCALED_FEATURES) + 1)  # + mode
    for name, value in values.items():
        row[SCALED_FEATURES.index(name)] = value
    return row


def test_reports_strongest_shared_traits_first():
    query = vector(energy=2.0, tempo=1.0, valence=-1.5)
    other = vector(energy=1.8, tempo=1.2, valence=-1.4)

    assert shared_traits(query, other) == ["mucha energía", "tono melancólico"]


def test_ignores_traits_in_opposite_directions():
    query = vector(energy=2.0, acousticness=1.0)
    other = vector(energy=-2.0, acousticness=1.0)

    assert shared_traits(query, other) == ["sonido acústico"]


def test_ignores_traits_close_to_the_average():
    assert shared_traits(vector(energy=0.2), vector(energy=0.3)) == []


def test_explain_falls_back_to_general_reason():
    assert explain(vector(), vector()) == GENERAL_REASON.capitalize()


def test_explain_joins_traits():
    query = vector(tempo=-1.0, loudness=1.0)

    assert explain(query, query) == "Comparten: volumen alto y tempo lento"

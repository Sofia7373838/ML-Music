import json

from api.monitoring import NAMESPACE, log_prediction


def test_event_follows_embedded_metric_format(capsys):
    log_prediction(
        endpoint="recommendations",
        model="knn",
        latency_ms=12.3456,
        track_id="a",
        k=5,
        recommended_ids=["b", "c"],
        recommended_popularity=[10, 30],
        recommended_explicit=1,
    )

    event = json.loads(capsys.readouterr().out)
    definition = event["_aws"]["CloudWatchMetrics"][0]
    assert definition["Namespace"] == NAMESPACE
    assert isinstance(event["_aws"]["Timestamp"], int)
    # Cada métrica y dimensión declarada debe existir como llave en la raíz del evento.
    for metric in definition["Metrics"]:
        assert metric["Name"] in event
    for dimension in definition["Dimensions"][0]:
        assert dimension in event
    assert event["Latency"] == 12.346
    assert event["Recommendations"] == 2
    assert event["RecommendedPopularity"] == [10, 30]
    assert event["ExplicitRecommended"] == 1


def test_not_found_counts_as_one(capsys):
    event = log_prediction(endpoint="recommendations", model="knn", latency_ms=1, found=False)

    assert event["SongNotFound"] == 1


def test_event_has_no_personal_data(capsys):
    event = log_prediction(endpoint="recommendations", model="knn", latency_ms=1, track_id="a")

    allowed = {
        "_aws",
        "Endpoint",
        "Latency",
        "Recommendations",
        "SongNotFound",
        "model",
        "track_id",
        "k",
        "max_popularity",
        "exclude_explicit",
        "max_per_artist",
        "recommended_ids",
        "RecommendedPopularity",
        "ExplicitRecommended",
    }
    assert set(event) == allowed

import pytest
from pydantic import TypeAdapter, ValidationError

from spotify_mcp_assistant import models


def test_normalization_preserves_original_indices():
    a, b = "spotify:track:" + "a" * 22, "spotify:track:" + "b" * 22
    assert models.normalize_uris([a, a, b], deduplicate=True) == ([a, b], [[0, 1], [2]])
    assert models.normalize_uris([a, a], deduplicate=False) == ([a, a], [[0], [1]])


@pytest.mark.parametrize(
    "value", ["spotify:album:" + "a" * 22, "spotify:track:short", ""]
)
def test_track_uri_rejects_wrong_resource(value):
    with pytest.raises(ValidationError):
        TypeAdapter(models.TrackURI).validate_python(value)


def test_device_id_strips_and_rejects_blank():
    assert TypeAdapter(models.DeviceID).validate_python(" x ") == "x"
    with pytest.raises(ValidationError):
        TypeAdapter(models.DeviceID).validate_python("  ")


def test_partial_result_keeps_error_and_progress():
    progress = models.MutationData(
        operation="add",
        status="unknown",
        target={},
        parameters={},
        requested_count=201,
        submitted_count=100,
        next_action="Read state",
        normalized_uris=[],
        input_indices=[],
        submitted_ranges=[(0, 100)],
        unknown_range=(100, 200),
        not_attempted_ranges=[(200, 201)],
    )
    result = models.BusinessResult[models.MutationData](
        ok=False,
        data=progress,
        error={
            "code": "write_result_unknown",
            "message": "Unknown",
            "next_action": "Read state",
            "retryable": False,
        },
    )
    payload = result.model_dump(mode="json")
    assert payload["data"]["submitted_ranges"] == [[0, 100]]
    assert payload["data"]["unknown_range"] == [100, 200]
    assert payload["error"]["code"] == "write_result_unknown"

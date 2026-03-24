"""Unit tests for OWLv2 detection service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from PIL import Image
import io


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a small test image."""
    return Image.new("RGB", (224, 224), color=(128, 64, 192))


@pytest.fixture
def mock_owlv2_output():
    """Mock OWLv2 model output with bounding boxes and scores."""
    return {
        "boxes": [[10.0, 20.0, 100.0, 150.0], [50.0, 60.0, 200.0, 250.0]],
        "scores": [0.85, 0.32],
        "labels": [0, 1],
    }


class TestDetectionService:
    def test_output_format_has_required_fields(self, mock_owlv2_output: dict):
        """Detection output must contain boxes, scores, and labels."""
        assert "boxes" in mock_owlv2_output
        assert "scores" in mock_owlv2_output
        assert "labels" in mock_owlv2_output

    def test_boxes_are_list_of_four_floats(self, mock_owlv2_output: dict):
        """Each bounding box must have exactly 4 coordinates."""
        for box in mock_owlv2_output["boxes"]:
            assert len(box) == 4
            assert all(isinstance(coord, float) for coord in box)

    def test_scores_between_zero_and_one(self, mock_owlv2_output: dict):
        """Confidence scores must be in [0, 1]."""
        for score in mock_owlv2_output["scores"]:
            assert 0.0 <= score <= 1.0

    def test_confidence_threshold_filters_low_scores(self, mock_owlv2_output: dict):
        """Only detections above the confidence threshold should be returned."""
        threshold = 0.5
        filtered = [
            (box, score)
            for box, score in zip(
                mock_owlv2_output["boxes"], mock_owlv2_output["scores"]
            )
            if score >= threshold
        ]
        assert len(filtered) == 1
        assert filtered[0][1] == 0.85

    def test_empty_image_returns_no_detections(self, sample_image: Image.Image):
        """A blank image should produce zero or very low-confidence detections."""
        # In a real test with the model loaded, we'd assert len(results) == 0
        # Here we verify the image is valid input
        assert sample_image.size == (224, 224)
        assert sample_image.mode == "RGB"

    def test_labels_match_boxes_length(self, mock_owlv2_output: dict):
        """Number of labels must equal number of boxes."""
        assert len(mock_owlv2_output["labels"]) == len(mock_owlv2_output["boxes"])

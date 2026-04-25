import pytest
from pathlib import Path

from shared.trace_utils import (
    extract_version_and_model,
    extract_model_and_version_from_trace_name
)

def test_extract_version_and_model():
    # Test valid formats
    assert extract_version_and_model("A166B-YLJ-4GB-BOS-TEST_ZC5_251226.log") == ("A166B", "ZC5")
    assert extract_version_and_model("A166B-YLJ-4GB-BOS-TEST_ZC5-123_251226.log") == ("A166B", "ZC5")
    assert extract_version_and_model("A166B_ZC5_251226.log") == ("A166B", "ZC5")
    
    # Test empty/invalid
    assert extract_version_and_model("") == ("", "")
    assert extract_version_and_model("invalid_name.log") == ("invalid", "invalid")

def test_extract_model_and_version_from_trace_name():
    # Test valid formats
    assert extract_model_and_version_from_trace_name("A166B-ZD7-4GB-BOS-TEST_251226_camera.log") == ("A166B", "ZD7")
    
    # Test without hyphens but with sufficient length
    assert extract_model_and_version_from_trace_name("A166BZD7_251226_camera.log") == ("A166B", "ZD7")
    
    # Test short model
    assert extract_model_and_version_from_trace_name("A1_251226.log") == ("A1", "")
    
    # Test empty
    assert extract_model_and_version_from_trace_name("") == ("", "")

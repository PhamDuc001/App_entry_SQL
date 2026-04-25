import pytest
from execution.processor import group_traces_by_app

def test_group_traces_by_app():
    trace_files = [
        "A166B-ZD7-4GB-BOS-TEST_251226_camera.log",
        "A166B-ZD7-4GB-BOS-TEST_251226_hello.log",
        "A166B-ZD7-4GB-BOS-TEST_251226_unknown.log"
    ]
    target_apps = ["camera", "hello", "unknown"]
    
    result = group_traces_by_app(trace_files, target_apps)
    
    # "unknown" should be ignored if not in APP_NAME_NORMALIZATION and TARGET_APPS
    # Actually, in group_traces_by_app, if it matches a target app, it is included.
    assert "camera" in result
    assert "hello" in result
    assert "unknown" in result
    
    assert len(result["camera"]) == 1
    assert result["camera"][0] == ("A166B-ZD7-4GB-BOS-TEST_251226_camera.log", 1)

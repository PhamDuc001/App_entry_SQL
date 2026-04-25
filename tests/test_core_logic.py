"""
Unit tests for core business logic functions.
Tests pure functions that don't require TraceProcessor or trace files.

Run: python -m pytest tests/test_core_logic.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================================
# 1. extract_version_and_model
# =========================================================================
class TestExtractVersionAndModel:
    """Test execution/json_output.py::extract_version_and_model"""

    def _func(self, path):
        from execution.json_output import extract_version_and_model
        return extract_version_and_model(path)

    def test_standard_filename(self):
        model, version = self._func("A166B-YLJ-4GB-BOS-TEST_ZC5_251226.log")
        assert model == "A166B"
        assert version == "ZC5"

    def test_simple_filename(self):
        model, version = self._func("A166B_ZC5_251226.log")
        assert model == "A166B"
        assert version == "ZC5"

    def test_two_parts(self):
        model, version = self._func("A166B_251226.log")
        assert model == "A166B"
        assert version == "251226"

    def test_single_part(self):
        model, version = self._func("A166B.log")
        assert model == ""
        assert version == ""

    def test_empty_string(self):
        model, version = self._func("")
        assert model == ""
        assert version == ""

    def test_none_input(self):
        model, version = self._func(None)
        assert model == ""
        assert version == ""

    def test_path_with_directory(self):
        model, version = self._func("/some/path/A166B-YLJ_ZC5_251226.log")
        assert model == "A166B"
        assert version == "ZC5"


# =========================================================================
# 2. extract_device_code
# =========================================================================
class TestExtractDeviceCode:
    """Test execution/json_output.py::extract_device_code"""

    def _func(self, title):
        from execution.json_output import extract_device_code
        return extract_device_code(title)

    def test_dash_separated(self):
        assert self._func("A166B-YLJ-4GB-BOS-TEST_251226") == "YLJ"

    def test_underscore_separated(self):
        assert self._func("A166B_YLJ_4GB_BOS_TEST_251226") == "YLJ"

    def test_single_part(self):
        assert self._func("A166B") == ""

    def test_empty(self):
        assert self._func("") == ""


# =========================================================================
# 3. group_traces_by_app
# =========================================================================
class TestGroupTracesByApp:
    """Test execution/processor.py::group_traces_by_app"""

    def _func(self, files, target_apps=None):
        from execution.processor import group_traces_by_app
        return group_traces_by_app(files, target_apps)

    def test_basic_grouping(self):
        files = [
            "/data/A166B_ZC5_251226_camera.log",
            "/data/A166B_ZC5_251226_clock.log",
            "/data/A166B_ZC5_251227_camera.log",
        ]
        result = self._func(files, ["camera", "clock"])
        assert "camera" in result
        assert "clock" in result
        assert len(result["camera"]) == 2
        assert len(result["clock"]) == 1

    def test_occurrence_tracking(self):
        files = [
            "/data/trace_251226_camera.log",
            "/data/trace_251227_camera.log",
            "/data/trace_251228_camera.log",
        ]
        result = self._func(files, ["camera"])
        occurrences = [occ for _, occ in result["camera"]]
        assert occurrences == [1, 2, 3]

    def test_filter_unmatched_apps(self):
        files = [
            "/data/trace_251226_camera.log",
            "/data/trace_251226_unknownapp.log",
        ]
        result = self._func(files, ["camera"])
        assert "camera" in result
        assert "unknownapp" not in result

    def test_empty_file_list(self):
        result = self._func([], ["camera"])
        assert result == {}

    def test_single_part_filename_skipped(self):
        files = ["/data/camera.log"]
        result = self._func(files, ["camera"])
        assert result == {}


# =========================================================================
# 4. get_filtered_metric_rows
# =========================================================================
class TestGetFilteredMetricRows:
    """Test execution/excel_sheet.py::get_filtered_metric_rows"""

    def _func(self, launch_type, app_name, has_cold, has_warm):
        from execution.excel_sheet import get_filtered_metric_rows
        return get_filtered_metric_rows(launch_type, app_name, has_cold, has_warm)

    def test_entry_cold_only(self):
        rows = self._func("entry", "camera", True, False)
        labels = [r[1] for r in rows]
        assert "App Execution Time" in labels
        assert "Start Proc" in labels
        assert "Touch Duration" not in labels

    def test_entry_warm_only(self):
        rows = self._func("entry", "clock", False, True)
        labels = [r[1] for r in rows]
        assert "App Execution Time" in labels
        assert "Touch Duration" in labels
        assert "Start Proc" not in labels

    def test_both_cold_warm(self):
        rows = self._func("entry", "camera", True, True)
        labels = [r[1] for r in rows]
        assert "Start Proc" in labels
        assert "Touch Duration" in labels

    def test_reentry_prefix(self):
        rows = self._func("reentry", "clock", True, False)
        first_label = rows[0][0]
        assert "2nd" in first_label


# =========================================================================
# 5. to_ms (sql_query/base.py)
# =========================================================================
class TestToMs:
    """Test sql_query/base.py::to_ms"""

    def _func(self, ns):
        from sql_query.base import to_ms
        return to_ms(ns)

    def test_basic_conversion(self):
        assert self._func(1000000) == 1.0

    def test_zero(self):
        assert self._func(0) == 0.0

    def test_large_value(self):
        assert self._func(1500000000) == 1500.0

    def test_fractional(self):
        result = self._func(1500000)
        assert abs(result - 1.5) < 0.001


# =========================================================================
# 6. _extract_timestamp_val (dumpstate_parser.py)
# =========================================================================
class TestExtractTimestampVal:
    """Test dumpstate_parser.py::_extract_timestamp_val"""

    def _func(self, filename):
        from dumpstate_parser import _extract_timestamp_val
        return _extract_timestamp_val(filename)

    def test_two_timestamps(self):
        result = self._func("trace_251226_143000_camera.log")
        assert result == 251226143000

    def test_single_timestamp(self):
        result = self._func("trace_251226_camera.log")
        assert result == 251226

    def test_no_timestamp(self):
        result = self._func("trace_camera.log")
        assert result == 0


# =========================================================================
# 7. APP_MAPPING and TARGET_APPS config
# =========================================================================
class TestAppConfig:
    """Test execution/config.py app configuration constants"""

    def test_app_mapping_not_empty(self):
        from execution.config import APP_MAPPING
        assert len(APP_MAPPING) > 0

    def test_app_mapping_has_camera(self):
        from execution.config import APP_MAPPING
        camera_entries = [v for v in APP_MAPPING.values() if "Camera" in v]
        assert len(camera_entries) > 0

    def test_target_apps_not_empty(self):
        from execution.config import TARGET_APPS
        assert len(TARGET_APPS) > 0

    def test_target_apps_contains_key_apps(self):
        from execution.config import TARGET_APPS
        for app in ["camera", "clock", "gallery", "internet"]:
            assert app in TARGET_APPS, f"{app} missing from TARGET_APPS"

    def test_cold_only_keys(self):
        from execution.config import COLD_ONLY_KEYS
        assert "Start Proc" in COLD_ONLY_KEYS
        assert isinstance(COLD_ONLY_KEYS, (set, frozenset))

    def test_warm_only_keys(self):
        from execution.config import WARM_ONLY_KEYS
        assert "Touch Duration" in WARM_ONLY_KEYS
        assert isinstance(WARM_ONLY_KEYS, (set, frozenset))

    def test_app_name_normalization(self):
        from execution.config import APP_NAME_NORMALIZATION
        assert APP_NAME_NORMALIZATION.get("calender") == "calendar"


# =========================================================================
# 8. parse_prio_key (execution/excel_sheet.py inner function - test via import)
# =========================================================================
class TestWriteValueOrEmpty:
    """Test execution/excel_sheet.py::write_value_or_empty via mock worksheet"""

    def test_zero_writes_empty(self):
        from execution.excel_sheet import write_value_or_empty
        calls = []

        class MockWS:
            def write(self, row, col, val, fmt):
                calls.append((row, col, val))

        write_value_or_empty(MockWS(), 0, 0, 0.0, None)
        assert calls[0][2] == ""

    def test_nonzero_writes_value(self):
        from execution.excel_sheet import write_value_or_empty
        calls = []

        class MockWS:
            def write(self, row, col, val, fmt):
                calls.append((row, col, val))

        write_value_or_empty(MockWS(), 0, 0, 42.5, None)
        assert calls[0][2] == 42.5

    def test_string_writes_value(self):
        from execution.excel_sheet import write_value_or_empty
        calls = []

        class MockWS:
            def write(self, row, col, val, fmt):
                calls.append((row, col, val))

        write_value_or_empty(MockWS(), 0, 0, "text", None)
        assert calls[0][2] == "text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

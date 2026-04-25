import pytest
import os
from sql_query.base import to_ms, get_resource_path

def test_to_ms():
    assert to_ms(1000000) == 1.0
    assert to_ms(1500000) == 1.5
    assert to_ms(0) == 0.0
    assert to_ms(None) == 0.0
    assert to_ms(-1000000) == -1.0

def test_get_resource_path():
    # Test typical path formatting
    relative_path = "perfetto/trace_processor.exe"
    absolute_path = get_resource_path(relative_path)
    
    # Just verify it returns an absolute path string containing our relative path
    assert os.path.isabs(absolute_path)
    assert relative_path.replace('/', os.sep) in absolute_path

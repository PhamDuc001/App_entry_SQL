# shared/excel_utils.py
"""
Shared Excel utility functions used by both execution and reaction modules.
"""


def write_value_or_empty(ws, row: int, col: int, value, fmt):
    """
    Write a value to an Excel cell. If the value is 0.0, empty, or None,
    write an empty string instead.

    Args:
        ws: xlsxwriter Worksheet object
        row: Row index (0-based)
        col: Column index (0-based)
        value: Value to write
        fmt: xlsxwriter Format object
    """
    if value == 0.0 or value == "" or value is None:
        ws.write(row, col, "", fmt)
    else:
        ws.write(row, col, value, fmt)

def write_value_or_empty(ws, row, col, value, fmt, empty_if_blank: bool = False):
    """Write value to Excel cell, or blank based on zero/blank rules."""
    is_zero = value == 0.0
    is_blank = value == "" or value is None
    if is_zero or (empty_if_blank and is_blank):
        ws.write(row, col, "", fmt)
    else:
        ws.write(row, col, value, fmt)

# shared/trace_utils.py
"""
Shared utility functions for trace file handling.
Consolidates duplicated functions from execution/ and reaction/ modules.
"""

from pathlib import Path
from typing import Tuple, List


def collect_trace_files(folder_path: str) -> List[str]:
    """
    Collect all .log files in a folder, sorted by name (A-Z).

    Args:
        folder_path: Path to folder containing trace files

    Returns:
        List of absolute file paths to .log files

    Raises:
        ValueError: If folder does not exist or is not a directory
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder không tồn tại: {folder_path}")

    return sorted([str(f) for f in folder.glob("*.log")])


def extract_version_and_model(file_path: str) -> Tuple[str, str]:
    """
    Extract model and version from the first trace filename.

    Example: A166B-YLJ-4GB-BOS-TEST_ZC5_251226.log
    -> model: A166B, version: ZC5

    Args:
        file_path: Path to a trace file

    Returns:
        (model, version) tuple, or ("", "") if parsing fails
    """
    if not file_path:
        return "", ""

    filename = Path(file_path).stem
    parts = filename.split('_')

    if len(parts) >= 2:
        model_part = parts[0]
        model = model_part.split('-')[0] if '-' in model_part else model_part

        version = parts[-2] if len(parts) >= 3 else parts[-1]
        version = version.split('-')[0] if '-' in version else version
        return model, version

    return "", ""


def extract_device_info(folder_path: str) -> Tuple[str, str, str]:
    """
    Extract model, version, and header_title from the first trace file in a folder.

    Consolidates the duplicated model/version parsing logic previously found
    in execution/main.py and reaction/main.py.

    Args:
        folder_path: Path to folder containing trace files

    Returns:
        (model, version, header_title) tuple
    """
    try:
        trace_files = collect_trace_files(folder_path)
    except ValueError:
        return "", "", "Metric"

    if not trace_files:
        return "", "", "Metric"

    first_file = Path(trace_files[0]).stem
    parts = first_file.split("_")
    header_title = "_".join(parts[:2]) if len(parts) >= 2 else first_file

    model = ""
    version = ""
    if parts:
        model_part = parts[0]
        if '-' in model_part:
            model = model_part.split('-')[0]
            version = model_part.split('-')[1]
        else:
            if len(model_part) >= 3:
                version = model_part[-3:]
                model = model_part[:-3].rstrip('-')

    return model, version, header_title


def extract_device_code(header_title: str) -> str:
    """
    Extract device code from header_title.

    Example:
    - A166B-YLJ-4GB-BOS-TEST_251226 -> YLJ
    - A166B_YLJ_4GB_BOS_TEST_251226 -> YLJ
    """
    normalized = header_title.replace('_', '-')
    parts = normalized.split('-')

    if len(parts) >= 2:
        return parts[1]

    return ""

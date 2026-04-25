from pathlib import Path
from typing import List, Tuple


def collect_trace_files(folder_path: str, raise_on_invalid: bool = False) -> List[str]:
    """Collect sorted .log files in a folder."""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        if raise_on_invalid:
            raise ValueError(f"Folder không tồn tại: {folder_path}")
        return []
    return sorted(str(f) for f in folder.glob("*.log"))


def extract_version_and_model(file_path: str) -> Tuple[str, str]:
    """
    Extract model/version from trace filename.
    Example: A166B-YLJ-4GB-BOS-TEST_ZC5_251226.log -> (A166B, ZC5)
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


def extract_model_and_version_from_trace_name(file_path: str) -> Tuple[str, str]:
    """
    Extract model/version from the first filename segment.
    Example: A166B-ZD7-4GB-BOS-TEST_... -> (A166B, ZD7)
    """
    if not file_path:
        return "", ""

    filename = Path(file_path).stem
    parts = filename.split("_")
    if not parts:
        return "", ""

    model_part = parts[0]
    if '-' in model_part:
        first_two = model_part.split('-')
        if len(first_two) >= 2:
            return first_two[0], first_two[1]
        return first_two[0], ""

    if len(model_part) >= 3:
        return model_part[:-3].rstrip('-'), model_part[-3:]

    return model_part, ""

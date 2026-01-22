#!/usr/bin/env python3
"""
Test script to verify the _extract_part_name method handles both naming patterns:
- "1part, 2part" (original pattern)
- "Part1, Part2" (new pattern)
"""

import re
from typing import Optional

def _extract_part_name(folder_name: str) -> Optional[str]:
    """Extract part name from folder name (e.g., 1part, 2part, Part1, Part2, etc.)"""
    # Look for patterns like 1part, 2part, Part1, Part2, etc. in the folder name
    # Handle both folder names and zip file names
    part_pattern = re.compile(r'((?:\d+part|part\d+))', re.IGNORECASE)
    match = part_pattern.search(folder_name)
    if match:
        # Normalize to lowercase format (e.g., "1part", "2part")
        part_name = match.group(1).lower()
        # Ensure consistent format: number before "part"
        if part_name.startswith('part'):

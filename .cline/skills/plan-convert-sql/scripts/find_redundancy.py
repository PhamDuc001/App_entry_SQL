#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_redundancy.py — Tìm code patterns lặp lại trong Python files

Phát hiện:
- Duplicate function calls (cùng function gọi nhiều lần trong 1 scope)
- Repeated file I/O patterns
- Similar code blocks (text similarity)
- Copy-paste fragments

Usage:
    python find_redundancy.py <file_path>
    python find_redundancy.py <file_path> --function <function_name>
"""

import ast
import sys
import os
from collections import defaultdict, Counter
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class RedundancyFinder(ast.NodeVisitor):
    """Tìm các patterns lặp lại trong code."""

    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.function_calls: Dict[str, List[Dict]] = defaultdict(list)
        self.io_calls: List[Dict] = []
        self.current_function = "<module>"
        self.current_loop_depth = 0
        self.warnings: List[str] = []

    def visit_FunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_For(self, node):
        self.current_loop_depth += 1
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_While(self, node):
        self.current_loop_depth += 1
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_Call(self, node):
        """Track mọi function call."""
        func_name = self._get_call_name(node)
        if func_name:
            info = {
                'name': func_name,
                'line': node.lineno,
                'in_function': self.current_function,
                'in_loop': self.current_loop_depth > 0,
                'loop_depth': self.current_loop_depth,
            }
            self.function_calls[func_name].append(info)

            # Detect I/O calls
            io_patterns = ['open', 'read', 'write', 'load', 'dump',
                          'find_dumpstate_content', 'get_memory_data',
                          'zipfile.ZipFile', 'json.load', 'json.dump',
                          'pickle.load', 'pickle.dump']
            if any(p in func_name for p in io_patterns):
                self.io_calls.append(info)

        self.generic_visit(node)

    def _get_call_name(self, node) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return node.func.attr
        return ""


def find_duplicate_calls(calls: Dict[str, List[Dict]]) -> List[Dict]:
    """Tìm function calls bị gọi nhiều lần trong cùng context."""
    duplicates = []

    for func_name, call_list in calls.items():
        # Group by containing function
        by_container = defaultdict(list)
        for call in call_list:
            by_container[call['in_function']].append(call)

        for container, container_calls in by_container.items():
            if len(container_calls) > 1:
                in_loop_count = sum(1 for c in container_calls if c['in_loop'])
                duplicates.append({
                    'function': func_name,
                    'count': len(container_calls),
                    'in': container,
                    'lines': [c['line'] for c in container_calls],
                    'in_loop_count': in_loop_count,
                    'severity': 'HIGH' if in_loop_count > 0 else 'MEDIUM',
                })

    return sorted(duplicates, key=lambda x: (x['severity'] == 'HIGH', x['count']), reverse=True)


def find_io_in_loops(io_calls: List[Dict]) -> List[Dict]:
    """Tìm I/O operations bên trong vòng lặp."""
    loop_io = [c for c in io_calls if c['in_loop']]
    return loop_io


def find_similar_blocks(source: str, min_lines: int = 4) -> List[Dict]:
    """Tìm các block code tương tự (simplified: exact line match)."""
    lines = source.split('\n')
    blocks = defaultdict(list)

    # Sliding window: Tìm các nhóm N dòng liên tiếp giống nhau
    for size in range(min_lines, min(20, len(lines))):
        for i in range(len(lines) - size + 1):
            block = '\n'.join(line.strip() for line in lines[i:i+size] if line.strip())
            if len(block) > 50:  # Bỏ qua block quá ngắn
                blocks[block].append({'start': i + 1, 'end': i + size})

    # Lọc ra chỉ những block xuất hiện > 1 lần
    duplicates = []
    seen_ranges = set()

    for block, locations in sorted(blocks.items(), key=lambda x: -len(x[0])):
        if len(locations) > 1:
            # Avoid overlapping reports
            key = tuple(loc['start'] for loc in locations)
            if key not in seen_ranges:
                seen_ranges.add(key)
                first_line = block.split('\n')[0][:80]
                duplicates.append({
                    'preview': first_line + "...",
                    'size': block.count('\n') + 1,
                    'count': len(locations),
                    'locations': locations,
                })

    return duplicates[:10]  # Top 10


def analyze_file(file_path: str):
    """Phân tích redundancy cho 1 file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        source = f.read()

    lines = source.split('\n')

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ SyntaxError: {e}")
        return

    finder = RedundancyFinder(lines)
    finder.visit(tree)

    print(f"\n{'='*70}")
    print(f"🔍 REDUNDANCY ANALYSIS: {file_path}")
    print(f"{'='*70}")

    # 1. Duplicate function calls
    duplicates = find_duplicate_calls(finder.function_calls)
    if duplicates:
        print(f"\n📋 DUPLICATE FUNCTION CALLS")
        print(f"  {'Function':<40} {'Count':>5} {'In':>25} {'In Loop':>8}")
        print(f"  {'-'*40} {'-'*5} {'-'*25} {'-'*8}")
        for d in duplicates[:20]:
            severity_icon = "🔴" if d['severity'] == 'HIGH' else "🟡"
            loop_str = f"{d['in_loop_count']}x" if d['in_loop_count'] else "-"
            print(f"  {severity_icon} {d['function']:<38} {d['count']:>5} {d['in']:>25} {loop_str:>8}")
            print(f"     Lines: {d['lines']}")
    else:
        print(f"\n✅ No duplicate function calls found.")

    # 2. I/O in loops
    loop_io = find_io_in_loops(finder.io_calls)
    if loop_io:
        print(f"\n⚠️  I/O OPERATIONS INSIDE LOOPS")
        for io in loop_io:
            print(f"  🔴 {io['name']}() at line {io['line']} (in {io['in_function']}, loop depth: {io['loop_depth']})")
    else:
        print(f"\n✅ No I/O operations inside loops.")

    # 3. Similar code blocks
    similar = find_similar_blocks(source)
    if similar:
        print(f"\n📋 SIMILAR CODE BLOCKS (potential copy-paste)")
        for s in similar[:5]:
            print(f"  🟡 {s['count']}x repeated ({s['size']} lines): \"{s['preview']}\"")
            locs = ', '.join(f"L{l['start']}-{l['end']}" for l in s['locations'][:3])
            print(f"     At: {locs}")

    # 4. Most called functions (top 10)
    print(f"\n📊 MOST CALLED FUNCTIONS")
    call_counts = {name: len(calls) for name, calls in finder.function_calls.items()}
    top_calls = sorted(call_counts.items(), key=lambda x: -x[1])[:10]
    for name, count in top_calls:
        print(f"  {name:<45} {count:>4}x")


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_redundancy.py <file_path>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isfile(target):
        analyze_file(target)
    elif os.path.isdir(target):
        for py_file in sorted(Path(target).rglob("*.py")):
            if '__pycache__' not in str(py_file):
                analyze_file(str(py_file))
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == '__main__':
    main()

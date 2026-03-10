#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_complexity.py — Phân tích complexity của file Python

Tính toán:
- Số lines, functions, classes
- Cyclomatic complexity (ước tính dựa trên control flow)
- Nesting depth tối đa
- Function quá dài (>50 lines)
- Import count

Usage:
    python analyze_complexity.py <file_path>
    python analyze_complexity.py <directory_path>   # Scan tất cả .py files
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class ComplexityVisitor(ast.NodeVisitor):
    """AST Visitor để đếm complexity indicators."""

    def __init__(self):
        self.functions: List[Dict] = []
        self.classes: List[str] = []
        self.imports: int = 0
        self.max_nesting: int = 0
        self._current_nesting: int = 0
        self._current_class: str = ""

    def visit_FunctionDef(self, node):
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_Import(self, node):
        self.imports += len(node.names)

    def visit_ImportFrom(self, node):
        self.imports += len(node.names) if node.names else 1

    def _analyze_function(self, node):
        """Phân tích một function node."""
        # Tính cyclomatic complexity (ước tính)
        complexity = 1  # Base
        max_nest = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp)):
                complexity += 1
            elif isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Assert):
                complexity += 1

        # Tính nesting depth
        max_nest = self._calc_max_nesting(node)

        # Tính số dòng
        if hasattr(node, 'end_lineno') and node.end_lineno:
            num_lines = node.end_lineno - node.lineno + 1
        else:
            num_lines = 0

        # Prefix class name
        full_name = f"{self._current_class}.{node.name}" if self._current_class else node.name

        self.functions.append({
            'name': full_name,
            'line': node.lineno,
            'end_line': getattr(node, 'end_lineno', 0),
            'lines': num_lines,
            'complexity': complexity,
            'max_nesting': max_nest,
            'args': len(node.args.args),
        })

        if max_nest > self.max_nesting:
            self.max_nesting = max_nest

    def _calc_max_nesting(self, node, depth=0):
        """Recursively calculate max nesting depth."""
        max_d = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With,
                                  ast.Try, ast.AsyncFor, ast.AsyncWith)):
                child_max = self._calc_max_nesting(child, depth + 1)
                if child_max > max_d:
                    max_d = child_max
            else:
                child_max = self._calc_max_nesting(child, depth)
                if child_max > max_d:
                    max_d = child_max
        return max_d


def analyze_file(file_path: str) -> Dict:
    """Phân tích complexity cho 1 file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        source = f.read()

    total_lines = source.count('\n') + 1
    blank_lines = sum(1 for line in source.split('\n') if not line.strip())
    comment_lines = sum(1 for line in source.split('\n') if line.strip().startswith('#'))

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            'file': file_path,
            'error': f"SyntaxError: {e}",
            'total_lines': total_lines,
        }

    visitor = ComplexityVisitor()
    visitor.visit(tree)

    return {
        'file': file_path,
        'total_lines': total_lines,
        'code_lines': total_lines - blank_lines - comment_lines,
        'blank_lines': blank_lines,
        'comment_lines': comment_lines,
        'num_functions': len(visitor.functions),
        'num_classes': len(visitor.classes),
        'num_imports': visitor.imports,
        'max_nesting': visitor.max_nesting,
        'functions': visitor.functions,
        'classes': visitor.classes,
    }


def print_report(result: Dict):
    """In báo cáo analysis."""
    if 'error' in result:
        print(f"\n❌ {result['file']}: {result['error']}")
        return

    print(f"\n{'='*70}")
    print(f"📄 {result['file']}")
    print(f"{'='*70}")

    # Summary
    print(f"\n📊 SUMMARY")
    print(f"  Total Lines:    {result['total_lines']:>6}")
    print(f"  Code Lines:     {result['code_lines']:>6}")
    print(f"  Blank Lines:    {result['blank_lines']:>6}")
    print(f"  Comment Lines:  {result['comment_lines']:>6}")
    print(f"  Functions:      {result['num_functions']:>6}")
    print(f"  Classes:        {result['num_classes']:>6}")
    print(f"  Imports:        {result['num_imports']:>6}")
    print(f"  Max Nesting:    {result['max_nesting']:>6}")

    # Functions sorted by complexity
    funcs = sorted(result['functions'], key=lambda x: x['complexity'], reverse=True)

    if funcs:
        print(f"\n🔍 TOP FUNCTIONS BY COMPLEXITY")
        print(f"  {'Name':<45} {'Lines':>6} {'CC':>4} {'Nest':>5} {'Args':>5}")
        print(f"  {'-'*45} {'-'*6} {'-'*4} {'-'*5} {'-'*5}")

        for func in funcs[:15]:
            marker = "⚠️" if func['complexity'] > 10 else "  "
            print(f"{marker}{func['name']:<45} {func['lines']:>6} {func['complexity']:>4} {func['max_nesting']:>5} {func['args']:>5}")

    # Warnings
    warnings = []
    for func in result['functions']:
        if func['lines'] > 100:
            warnings.append(f"  🔴 {func['name']}: {func['lines']} lines (quá dài, nên tách)")
        elif func['lines'] > 50:
            warnings.append(f"  🟡 {func['name']}: {func['lines']} lines (dài, cân nhắc tách)")
        if func['complexity'] > 15:
            warnings.append(f"  🔴 {func['name']}: CC={func['complexity']} (complex, nên refactor)")
        elif func['complexity'] > 10:
            warnings.append(f"  🟡 {func['name']}: CC={func['complexity']} (khá complex)")
        if func['max_nesting'] > 5:
            warnings.append(f"  🔴 {func['name']}: Nesting={func['max_nesting']} (quá sâu)")
        if func['args'] > 7:
            warnings.append(f"  🟡 {func['name']}: {func['args']} args (nhiều params, cân nhắc dùng dict/dataclass)")

    if warnings:
        print(f"\n⚠️  WARNINGS")
        for w in warnings:
            print(w)
    else:
        print(f"\n✅ No warnings — code looks clean!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_complexity.py <file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isfile(target):
        result = analyze_file(target)
        print_report(result)
    elif os.path.isdir(target):
        py_files = sorted(Path(target).rglob("*.py"))
        if not py_files:
            print(f"No .py files found in {target}")
            sys.exit(1)

        all_results = []
        for py_file in py_files:
            if '__pycache__' in str(py_file) or '.git' in str(py_file):
                continue
            result = analyze_file(str(py_file))
            all_results.append(result)
            print_report(result)

        # Summary across all files
        total_lines = sum(r.get('total_lines', 0) for r in all_results)
        total_funcs = sum(r.get('num_functions', 0) for r in all_results)
        print(f"\n{'='*70}")
        print(f"📊 OVERALL: {len(all_results)} files, {total_lines} lines, {total_funcs} functions")
        print(f"{'='*70}")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == '__main__':
    main()

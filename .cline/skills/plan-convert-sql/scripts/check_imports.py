#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_imports.py — Kiểm tra import thừa/thiếu trong Python files

Phát hiện:
- Unused imports (import nhưng không dùng)
- Potentially missing imports (tên được dùng nhưng không có import)
- Wildcard imports (from module import *)
- Circular import candidates (A imports B, B imports A)

Usage:
    python check_imports.py <file_path>
    python check_imports.py <directory_path>
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class ImportAnalyzer(ast.NodeVisitor):
    """Phân tích imports và usage trong Python file."""

    def __init__(self):
        # Tất cả imported names: {name: line_number}
        self.imported_names: Dict[str, int] = {}
        # Import statements gốc: [(module, names, line)]
        self.import_stmts: List[Dict] = []
        # Wildcard imports
        self.wildcard_imports: List[Dict] = []
        # Tất cả names được sử dụng (không phải import)
        self.used_names: Set[str] = set()
        # Import modules (for circular check)
        self.imported_modules: List[str] = []
        # Tracking context
        self._in_import = False

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = node.lineno
            self.imported_modules.append(alias.name)
            self.import_stmts.append({
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
            })

    def visit_ImportFrom(self, node):
        module = node.module or ''
        self.imported_modules.append(module)

        if node.names:
            for alias in node.names:
                if alias.name == '*':
                    self.wildcard_imports.append({
                        'module': module,
                        'line': node.lineno,
                    })
                else:
                    name = alias.asname if alias.asname else alias.name
                    self.imported_names[name] = node.lineno
                    self.import_stmts.append({
                        'type': 'from',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                    })

    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Track module.attribute usage (e.g., os.path)
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Function name is "defined", not "used" in import context
        # But decorators and defaults ARE usage
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults + node.args.kw_defaults:
            if default:
                self.visit(default)
        # Visit annotations
        if node.returns:
            self.visit(node.returns)
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation:
                self.visit(arg.annotation)
        # Visit body
        for child in node.body:
            self.visit(child)

    def visit_ClassDef(self, node):
        # Bases and decorators are usage
        for base in node.bases:
            self.visit(base)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for child in node.body:
            self.visit(child)


def analyze_file(file_path: str) -> Dict:
    """Phân tích imports cho 1 file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {'file': file_path, 'error': str(e)}

    analyzer = ImportAnalyzer()
    analyzer.visit(tree)

    # Tìm unused imports
    # Loại trừ: names dùng trong type hints có thể bị miss bởi AST
    unused = {}
    for name, line in analyzer.imported_names.items():
        if name not in analyzer.used_names:
            # Kiểm tra thêm: có thể dùng trong string annotations
            if name not in source.replace(f"import {name}", "").replace(f"from", ""):
                unused[name] = line

    # Tìm names có thể thiếu import (heuristic)
    # Builtin names to exclude
    builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
    builtins.update({
        'self', 'cls', 'None', 'True', 'False',
        'print', 'range', 'len', 'str', 'int', 'float', 'list', 'dict',
        'set', 'tuple', 'bool', 'type', 'super', 'property',
        'staticmethod', 'classmethod', 'enumerate', 'zip', 'map', 'filter',
        'sorted', 'reversed', 'min', 'max', 'sum', 'abs', 'round',
        'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
        'open', 'input', 'iter', 'next', 'any', 'all',
        'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError',
        'Exception', 'RuntimeError', 'StopIteration', 'FileNotFoundError',
        'OSError', 'IOError', 'ImportError', 'NotImplementedError',
        'UnicodeDecodeError', 'UnicodeError',
    })

    return {
        'file': file_path,
        'total_imports': len(analyzer.imported_names),
        'unused': unused,
        'wildcard': analyzer.wildcard_imports,
        'modules': analyzer.imported_modules,
        'stmts': analyzer.import_stmts,
    }


def find_circular_candidates(results: List[Dict]) -> List[Tuple[str, str]]:
    """Tìm potential circular imports giữa các files."""
    # Map: file → imported modules
    file_imports = {}
    for r in results:
        if 'error' in r:
            continue
        basename = Path(r['file']).stem
        file_imports[basename] = set(
            Path(m).stem if '.' not in m else m.split('.')[-1]
            for m in r.get('modules', [])
        )

    # Check A→B and B→A
    circular = []
    checked = set()
    for file_a, imports_a in file_imports.items():
        for file_b in imports_a:
            if file_b in file_imports:
                if file_a in file_imports[file_b]:
                    pair = tuple(sorted([file_a, file_b]))
                    if pair not in checked:
                        checked.add(pair)
                        circular.append(pair)
    return circular


def print_report(result: Dict):
    """In báo cáo cho 1 file."""
    if 'error' in result:
        print(f"\n❌ {result['file']}: {result['error']}")
        return

    print(f"\n{'='*60}")
    print(f"📦 {result['file']}")
    print(f"   Total imports: {result['total_imports']}")

    # Unused
    if result['unused']:
        print(f"\n   ⚠️  UNUSED IMPORTS ({len(result['unused'])})")
        for name, line in sorted(result['unused'].items(), key=lambda x: x[1]):
            print(f"      Line {line:>4}: {name}")
    else:
        print(f"   ✅ No unused imports")

    # Wildcards
    if result['wildcard']:
        print(f"\n   🔴 WILDCARD IMPORTS (uncontrolled namespace)")
        for w in result['wildcard']:
            print(f"      Line {w['line']:>4}: from {w['module']} import *")

    # Summary
    stmts = result.get('stmts', [])
    if stmts:
        from_imports = [s for s in stmts if s['type'] == 'from']
        direct_imports = [s for s in stmts if s['type'] == 'import']
        print(f"\n   📊 Breakdown: {len(direct_imports)} direct, {len(from_imports)} from-imports")


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_imports.py <file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isfile(target):
        result = analyze_file(target)
        print_report(result)
    elif os.path.isdir(target):
        results = []
        for py_file in sorted(Path(target).rglob("*.py")):
            if '__pycache__' in str(py_file) or '.git' in str(py_file):
                continue
            result = analyze_file(str(py_file))
            results.append(result)
            print_report(result)

        # Check circular imports
        circular = find_circular_candidates(results)
        if circular:
            print(f"\n{'='*60}")
            print(f"🔄 POTENTIAL CIRCULAR IMPORTS")
            for a, b in circular:
                print(f"   ⚠️  {a} ↔ {b}")
        
        # Overall summary
        total_unused = sum(len(r.get('unused', {})) for r in results)
        total_wildcard = sum(len(r.get('wildcard', [])) for r in results)
        print(f"\n{'='*60}")
        print(f"📊 OVERALL: {len(results)} files, {total_unused} unused imports, {total_wildcard} wildcards")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == '__main__':
    main()

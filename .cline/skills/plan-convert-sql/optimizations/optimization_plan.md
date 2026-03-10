# Performance Optimization Plan for Memory & Pageboost Modes

## Analysis Summary

### Memory Mode (MemoryStatus/memory_main.py)

**Current Bottlenecks:**
1. **File I/O in loops**: `collect_folder_data()` opens and parses files sequentially
2. **Multiple full folder scans**: Creates 4 Excel files, each requiring full folder scan
3. **Regex parsing on every line**: `parse_mem_file()` uses regex on every line
4. **No caching**: Re-parses same files for each Excel file
5. **Redundant data collection**: Collects same data 4 times (first, re-entry, start/end)

**Performance Impact:**
- For 100 apps × 20 cycles × 4 Excel files = 8000 file operations
- Each file ~50KB → ~400MB of I/O operations
- Estimated time: 30-60 seconds for large datasets

### Pageboost Mode (Pageboostd/pageboost_main.py)

**Current Bottlenecks:**
1. **ZIP extraction to disk**: `extract_largest_file_from_zip()` extracts before parsing
2. **Multiple directory walks**: `collect_cycles_from_extracted()` walks entire structure
3. **Sequential processing**: Processes files one by one
4. **Temporary folder overhead**: Creates/deletes `_tmp` folder
5. **No caching**: Re-reads same ZIP files multiple times

**Performance Impact:**
- For 100 apps × 20 cycles × 2 folders = 4000 file operations
- Each ZIP ~10MB → ~40GB extraction + parsing
- Estimated time: 60-120 seconds for large datasets

### dumpstate_parser.py (Shared)

**Current Bottlenecks:**
1. **String operations on large files**: `find_dumpstate_content()` loads entire dumpstate
2. **Regex not pre-compiled**: Some patterns compiled per function call
3. **Multiple regex searches**: Searches same content multiple times

## Optimization Strategy

### Phase 1: Memory Mode Optimizations

1. **Pre-compile regex patterns at module level**
2. **Implement caching system** for parsed memory files
3. **Parallel file parsing** with multiprocessing
4. **Reuse data across Excel files** (parse once, use 4x)
5. **Early termination** when MemFree & MemAvailable found

**Expected Speedup**: 3-5x

### Phase 2: Pageboost Mode Optimizations

1. **Stream ZIP content directly** (no disk extraction)
2. **Parallel ZIP processing** with multiprocessing
3. **Cache largest file info** per folder
4. **Pre-compiled regex patterns**
5. **Batch data collection** for all cycles

**Expected Speedup**: 4-6x

### Phase 3: dumpstate_parser Optimizations

1. **Pre-compile all regex patterns** at module level
2. **Lazy parsing** (only parse needed sections)
3. **Cache dumpstate content** per file
4. **Optimize string operations**

**Expected Speedup**: 2-3x

## Implementation Order

1. ✅ Analyze current code
2. 🔲 Optimize Memory mode
3. 🔲 Optimize Pageboost mode
4. 🔲 Optimize dumpstate_parser
5. 🔲 Test with real data
6. 🔲 Document results

## Testing Strategy

1. **Benchmark before/after** on same dataset
2. **Verify data correctness** (compare outputs)
3. **Test with various sizes** (small, medium, large)
4. **Memory profiling** (check for leaks)
5. **Edge case testing** (missing files, empty folders)

## Success Metrics

- **Memory mode**: < 15 seconds (currently 30-60s)
- **Pageboost mode**: < 20 seconds (currently 60-120s)
- **Data correctness**: 100% match with original outputs
- **Memory usage**: No significant increase
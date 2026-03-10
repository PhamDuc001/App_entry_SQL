# Abnormal Memory Analysis Optimization Plan

## Problem Statement
The abnormal memory analysis (abnormal_memory.py) takes too long to create DevicePerformance Excel reports.
Current performance: 5-10 minutes for typical datasets
Target performance: 1-2 minutes (3-5x speedup)

## Performance Bottlenecks

### 1. ZIP Extraction to Disk (Major Bottleneck)
**Current:**
```python
def extract_largest_file_from_zip(self, zip_path: Path, extract_dir: Path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        largest = max(infos, key=lambda x: x.file_size)
        with open(cache_path, "wb") as f:
            f.write(z.read(largest))  # Write to disk
    return cache_path  # Then read from disk again
```

**Impact:** 40-60% of total execution time
**Issue:** Disk I/O is slow, especially over network shares

**Solution:** Stream ZIP content directly to memory
```python
def parse_zip_content_directly(zip_path: Path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        largest = max(infos, key=lambda x: x.file_size)
        with z.open(largest) as f:
            content = f.read().decode('utf-8')  # Read to memory
        return parse_content(content)  # Parse directly from memory
```

**Expected Speedup:** 10-20x for ZIP operations

### 2. Multiple File Reads (Major Bottleneck)
**Current:**
- Read file for uptime analysis
- Read file again for crash analysis
- Read file again for I/O analysis
- Read file again for PSS analysis
- Read file again for compiler info
- Read file again for app start/kill analysis

**Impact:** Each dumpstate file read 5-6 times

**Solution:** Single-pass parsing - extract all data in one read
```python
def parse_file_comprehensive(file_path: Path) -> ParseResult:
    """Parse all required data in a single file read"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract all data in one pass
    uptime = extract_uptime(content)
    crashes = extract_crashes(content)
    io_read, io_write = extract_io_data(content)
    pss_data = extract_pss_data(content)
    compiler_info = extract_compiler_info(content)
    app_start_kill = extract_app_start_kill(content)
    
    return ParseResult(uptime, crashes, io_read, io_write, pss_data, 
                      compiler_info, app_start_kill)
```

**Expected Speedup:** 3-5x reduction in file I/O

### 3. No Caching
**Current:** Every parse operation reads the file again

**Solution:** LRU cache for parsed dumpstate files
```python
from functools import lru_cache

@lru_cache(maxsize=256)
def parse_dumpstate_cached(file_path: str) -> ParseResult:
    return parse_dumpstate(file_path)

def clear_cache():
    parse_dumpstate_cached.cache_clear()
```

**Expected Speedup:** Avoid re-parsing same files multiple times

### 4. Sequential Processing
**Current:** Files processed one by one in main thread

**Solution:** Parallel processing with multiprocessing
```python
from multiprocessing import Pool, cpu_count

def process_all_files_parallel(file_paths: List[Path]) -> List[ParseResult]:
    num_workers = min(cpu_count(), len(file_paths))
    with Pool(processes=num_workers) as pool:
        results = pool.map(parse_dumpstate_cached, file_paths)
    return results
```

**Expected Speedup:** 4-8x on multi-core systems

### 5. Redundant PSS Parsing
**Current:** PSS data extracted multiple times for different thresholds

**Solution:** Extract PSS data once, filter on-demand
```python
def extract_all_pss_data(content: str) -> List[Tuple[str, float]]:
    """Extract all PSS data once, return list of (process, pss_mb)"""
    # Extract all PSS entries
    return all_pss_entries

def filter_pss_by_threshold(pss_data: List[Tuple[str, float]], threshold: float) -> List[Tuple[str, float]]:
    """Filter pre-extracted PSS data by threshold"""
    return [(proc, pss) for proc, pss in pss_data if pss > threshold]
```

**Expected Speedup:** 2-3x for PSS analysis

### 6. Regex Compilation in Loops
**Current:** Regex patterns compiled on every function call

**Solution:** Pre-compile patterns at module level
```python
# Module level
UPTIME_PATTERN = re.compile(r"Uptime:\s+up\s+(.+?),\s+load average:")
ANR_PATTERN = re.compile(r"ANR in (.+?)(?:\s+\(pid\s+(\d+)\))?")
FATAL_PATTERN = re.compile(r"FATAL EXCEPTION: (.+?)(?:\s+pid\s+(\d+))?")
IO_PATTERN = re.compile(r"(Read_top|Write_top)\(KB\):\s*(.*)")
PSS_PATTERN = re.compile(r'\s+(\d{1,3}(?:,\d{3})*)K:\s*([^\s\(]+)')
COMPILER_PATTERN = re.compile(r"\[ro\.boot\.debug_level\]:\s*\[(0x[0-9a-fA-F]+)\]")
```

**Expected Speedup:** 2-3x for regex-heavy operations

## Implementation Plan

### Phase 1: Core Optimizations (High Impact)
1. ✅ Pre-compile regex patterns at module level
2. ✅ Implement single-pass parsing function
3. ✅ Stream ZIP content directly (no disk extraction)
4. ✅ Add LRU cache for parsed results

### Phase 2: Parallel Processing (Medium Impact)
5. ✅ Implement multiprocessing for independent file parsing
6. ✅ Optimize thread pool usage for ZIP extraction

### Phase 3: Data Structure Optimizations (Low Impact)
7. ✅ Optimize PSS data extraction (extract once, filter multiple times)
8. ✅ Optimize I/O data aggregation (use heapq instead of full sort)
9. ✅ Cache RAM size and debug level detection

## Expected Performance Improvements

| Optimization | Current Time | Optimized Time | Speedup |
|-------------|--------------|----------------|---------|
| ZIP streaming | 40s | 4s | **10x** |
| Single-pass parsing | 30s | 10s | **3x** |
| Caching | 20s | 10s | **2x** |
| Parallel processing | 60s | 15s | **4x** |
| **Overall** | **5-10 min** | **1-2 min** | **5-8x** |

## Risk Assessment

### Low Risk
- Pre-compiled regex patterns (no logic change)
- Caching (transparent to caller)
- Single-pass parsing (same output, different implementation)

### Medium Risk
- ZIP streaming (need to handle memory for large files)
- Parallel processing (need to handle exceptions properly)

### Mitigations
- Limit cache size to prevent memory issues
- Add memory monitoring for large ZIP files
- Proper exception handling in parallel workers
- Fallback to original implementation if errors occur

## Testing Plan

1. **Functional Testing**
   - Verify Excel output matches original
   - Check all sheets contain correct data
   - Test with small, medium, large datasets

2. **Performance Testing**
   - Benchmark before/after optimization
   - Measure memory usage
   - Check for memory leaks

3. **Edge Cases**
   - Empty folders
   - Missing dumpstate files
   - Corrupted ZIP files
   - Very large dumpstate files (>1GB)

## Rollback Plan

If optimizations cause issues:
1. Keep original functions as `_original_*` versions
2. Add flag to enable/disable optimizations
3. Provide fallback to original implementation
4. Detailed logging for debugging

## Success Criteria

✅ Execution time reduced to <2 minutes (from 5-10 min)
✅ 100% data correctness (Excel output identical)
✅ No memory leaks
✅ Handles all edge cases
✅ Backward compatible with existing code
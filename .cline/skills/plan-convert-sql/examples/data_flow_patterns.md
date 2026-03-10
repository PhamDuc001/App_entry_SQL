# Data Flow Patterns — Python Dev Kit

Các patterns phổ biến khi xử lý data pipeline trong Python, đặc biệt cho các tool phân tích batch data.

---

## Pattern 1: Worker Pre-Compute → Consumer Read

**Khi nào dùng:** Nhiều consumers cần cùng data từ 1 nguồn expensive.

```
┌─────────┐    ┌──────────────────┐    ┌────────────┐
│  Source  │───▶│   Worker Pool    │───▶│   Cache    │
│ (zip/db) │    │ (pre-compute)    │    │ (dict/pkl) │
└─────────┘    └──────────────────┘    └─────┬──────┘
                                             │
                    ┌────────────────────────┬┘
                    ▼                        ▼
              ┌──────────┐           ┌──────────┐
              │ Excel    │           │ JSON     │
              │ Consumer │           │ Consumer │
              └──────────┘           └──────────┘
```

```python
# WORKER: Đọc 1 lần, parse tất cả, lưu dict
def worker(file_path, config):
    raw = expensive_read(file_path)   # 1 lần I/O
    return {
        'metric_a': parse_a(raw),     # Parse ngay
        'metric_b': parse_b(raw),     # Parse ngay
        'metric_c': parse_c(raw),     # Parse ngay
        'raw_summary': summarize(raw) # Tóm tắt nếu cần
    }
    # raw bị GC sau khi worker return → tiết kiệm RAM

# CONSUMER: Chỉ đọc kết quả, KHÔNG đọc lại raw
def write_excel(precomputed):
    a = precomputed.get('metric_a', 0)   # O(1) dict lookup
    b = precomputed.get('metric_b', 0)   # Không I/O
```

---

## Pattern 2: Collect → Aggregate → Output

**Khi nào dùng:** Cần tổng hợp data từ nhiều cycles/iterations.

```python
# STEP 1: COLLECT - Thu thập raw values
values_per_cycle = []
for cycle in cycles:
    val = cycle.get('metric', 0)
    if val > 0:
        values_per_cycle.append(val)

# STEP 2: AGGREGATE - Tính toán thống kê
if values_per_cycle:
    avg = sum(values_per_cycle) / len(values_per_cycle)
    max_val = max(values_per_cycle)
    min_val = min(values_per_cycle)

# STEP 3: OUTPUT - Ghi kết quả
result['metric_avg'] = round(avg, 3)
```

---

## Pattern 3: Mapping & Cross-Reference

**Khi nào dùng:** Cần map data giữa 2 sources (VD: DUT vs REF).

```python
# STEP 1: Build lookup from one source
ref_map = {}
for item in ref_data:
    key = item['name']           # Dùng tên làm key
    ref_map[key] = item['value'] # O(1) lookup sau này

# STEP 2: Iterate other source, lookup match
results = []
for dut_item in dut_data:
    dut_val = dut_item['value']
    ref_val = ref_map.get(dut_item['name'], 0)  # O(1) lookup
    diff = dut_val - ref_val
    results.append({
        'name': dut_item['name'],
        'dut': dut_val,
        'ref': ref_val,
        'diff': diff,
    })

# STEP 3: Sort by diff for ranking
top_results = sorted(results, key=lambda x: x['diff'], reverse=True)[:10]
```

---

## Pattern 4: Incremental Cache (Smart Cache)

**Khi nào dùng:** Xử lý batch lớn, muốn tránh re-process khi chạy lại.

```python
import pickle

CACHE_VERSION = "1.0"

def get_or_process(folder, target_items):
    cache_path = os.path.join(folder, ".cache.pkl")
    
    # 1. Load cache
    cached = {}
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
        if cache.get('version') == CACHE_VERSION:
            cached = cache.get('data', {})
    
    # 2. Find missing items
    missing = [item for item in target_items if item not in cached]
    
    if not missing:
        return cached  # ⚡ Full cache hit
    
    # 3. Process ONLY missing items
    new_data = process_items(missing)
    
    # 4. Merge & save
    merged = {**cached, **new_data}
    with open(cache_path, 'wb') as f:
        pickle.dump({'version': CACHE_VERSION, 'data': merged}, f)
    
    return merged
```

---

## Pattern 5: Multiprocessing with Shared State

**Khi nào dùng:** CPU-bound tasks cần parallel processing.

```python
from multiprocessing import Pool

# ⚠️ RULES:
# 1. Worker function PHẢI là top-level (không phải method/lambda/closure)
# 2. Arguments PHẢI pickle-able (không truyền file handles, connections)
# 3. Return value PHẢI pickle-able

def worker_func(args):
    """Top-level function — serializable."""
    file_path, config_dict = args
    # Mỗi worker tự mở resources riêng
    result = process(file_path, config_dict)
    return result

def main():
    tasks = [(f, config) for f in files]
    
    with Pool(processes=num_workers) as pool:
        # imap: Trả kết quả theo thứ tự, lazy evaluation
        for i, result in enumerate(pool.imap(worker_func, tasks)):
            print(f"[{i+1}/{len(tasks)}] Done")
            save_result(result)
```

---

## Pattern 6: Conditional Data Extension

**Khi nào dùng:** Thêm data mới vào pipeline mà không ảnh hưởng code cũ.

```python
# Backward-compatible extension
metrics = analyze_trace(tp, file_path)     # Code cũ
metrics['new_field'] = compute_new(data)    # Thêm mới

# Consumer code cũ vẫn hoạt động (dùng .get với default)
old_val = metrics.get('old_field', 0)       # ✅ Vẫn OK
new_val = metrics.get('new_field', 0)       # ✅ Consumer mới
missing = metrics.get('future_field', 0)    # ✅ Trả về default, không crash
```

---

## Anti-Patterns (TRÁNH)

### ❌ Anti-Pattern 1: Re-Read in Loop
```python
for metric in metrics:
    content = read_file(path)  # Đọc lại file mỗi iteration!
    val = parse(content, metric)
```

### ❌ Anti-Pattern 2: N+1 Query
```python
for item in items:
    detail = db.query(f"SELECT * WHERE id={item.id}")  # N queries!
```

### ❌ Anti-Pattern 3: Accumulate in Memory without Bound
```python
all_data = []
for f in thousands_of_files:
    all_data.append(read_entire_file(f))  # OOM risk
```

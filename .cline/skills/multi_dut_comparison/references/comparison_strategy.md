# Multi-DUT Comparison Strategy

## Normalization Rules

### App Matching
- Match by `app` field name (exact, lowercase)
- Only compare apps present in **ALL** DUT files
- Flag apps missing from specific DUTs

### Metric Comparison

#### Absolute Diff
```
diff = DUT.metric - REF.metric
```
Use for: Running, Sleeping, Runnable, D-state, Execution Time, Binder count

#### Relative Diff (%)
```
pct_diff = (DUT.metric - REF.metric) / REF.metric * 100
```
Use for: Frequency%, Priority%, PSS, Pageboost (to compare across different RAM sizes fairly)

### Cross-DUT Aggregation

| Method | When to Use |
|--------|------------|
| **Median** | Default for timing metrics (robust against outliers) |
| **Range** | Show best/worst performer spread |
| **Standard Deviation** | Detect inconsistent behavior across DUTs |

## Pattern Detection Algorithms

### Common Issue Detection
```
IS_COMMON = (metric exceeds threshold for ALL DUTs)
```

### Variant Correlation
```
Sort DUTs by RAM size (ascending)
If metric severity correlates with RAM → "Memory-sensitive issue"
If metric severity independent of RAM → "Software/config issue"
```

### Outlier Detection
```
For each DUT:
  z_score = (DUT.metric - mean_all_DUTs) / std_all_DUTs
  If |z_score| > 2.0 → Flag as outlier
```

## Comparison Scope

| Level | Compare |
|-------|---------|
| **Overview** | Execution time, pass/fail per app |
| **State Analysis** | Running, Sleeping, Runnable, D-state |
| **Environment** | Memory, compiler, uptime, pageboost |
| **Detailed** | Frequency, priority, top CPU, block I/O (per cycle) |

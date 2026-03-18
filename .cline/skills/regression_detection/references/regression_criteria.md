# Regression Detection Criteria

## Change Classification Matrix

```
                    Absolute Change
                Small (<threshold)    Large (>threshold)
Relative    Small (<5%)    NOISE           EXPECTED VARIANCE
Change      Large (>5%)    INVESTIGATE     REGRESSION/IMPROVEMENT
```

## Per-Metric Thresholds

### Timing Metrics (ms)

| Metric | Noise (ignore) | Investigate | Regression | Major |
|--------|----------------|-------------|------------|-------|
| App Execution Time | <10ms | 10-30ms | 30-100ms | >100ms |
| Running | <5ms | 5-20ms | 20-50ms | >50ms |
| Sleeping | <5ms | 5-20ms | 20-50ms | >50ms |
| Runnable | <3ms | 3-10ms | 10-30ms | >30ms |
| D-state | <3ms | 3-15ms | 15-30ms | >30ms |
| Section (bind/start/resume/choreo) | <3ms | 3-10ms | 10-30ms | >30ms |

### Resource Metrics

| Metric | Noise | Investigate | Regression | Major |
|--------|-------|-------------|------------|-------|
| Binder count | ±5 | 5-10 | 10-25 | >25 |
| Binder duration (ms) | <5ms | 5-15ms | 15-50ms | >50ms |
| PSS (MB) | <5MB | 5-20MB | 20-50MB | >50MB |
| MemFree (MB) | <20MB | 20-50MB | 50-100MB | >100MB |
| Pageboost (MB) | <2MB | 2-5MB | 5-10MB | >10MB |

### Distribution Metrics

| Metric | Noise | Significant |
|--------|-------|-------------|
| Frequency at max (%) | <3% | >10% |
| Priority at 110 (%) | <3% | >10% |

## Trend Analysis

### 3+ Versions Available
```
Linear regression across versions:
- Positive slope + R² > 0.7 → "Gradual degradation"
- Negative slope + R² > 0.7 → "Gradual improvement"
- One outlier point → "Spike/anomaly at version X"
- Random → "Unstable/noisy metric"
```

### 2 Versions Available
```
Simple comparison:
- Change > threshold → Regression or Improvement
- Change < noise → Stable
```

## Correlation Checks

Khi phát hiện regression, check these correlations:

| If this regressed | Also check | Likely correlation |
|-------------------|------------|-------------------|
| Running ↑ | compiler changed? | Yes → compiler issue |
| Running ↑ | max frequency ↓? | Yes → frequency issue |
| Sleeping ↑ | binder count ↑? | Yes → binder issue |
| D-state ↑ | MemFree ↓? | Yes → memory pressure |
| D-state ↑ | Pageboost ↓? | Yes → pageboost regression |
| Execution ↑ | State changed (Warm→Cold)? | Yes → start state issue |

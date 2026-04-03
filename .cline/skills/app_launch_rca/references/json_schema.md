# JSON Output Schema – execution_sql Pipeline (v3 – Per-Cycle)

## File Types

| Type | Filename Pattern | Content |
|------|-----------------|---------|
| DUT data | `DUT_<model>_<version>_<timestamp>.json` | DUT device data |
| REF data | `REF_<model>_<version>_<timestamp>.json` | Reference baseline data |

Cả DUT và REF đều có cùng schema, phân biệt qua field `type`.

---

## Root Level

```json
{
  "model": "A266M",             // Device model
  "device_code": "8GB",         // RAM size hoặc device variant
  "version": "ZA1",             // Software version (build version)
  "timestamp": "2026-04-02T19:15:35.294223",
  "type": "DUT",                // "DUT" hoặc "REF"
  "apps_data": [...]            // Array of app entries
}
```

---

## Per App Entry (`apps_data[i]`)

```json
{
  "app": "calculator",          // App name (lowercase)
  "entry": { ... }              // Entry launch data (cold start)
}
```

> **Note**: Một số file có thể chứa thêm `"reentry"` cho warm start data.

---

## Entry Object (`apps_data[i].entry`)

### State
```json
"State": ["Cold", "Cold", "Cold"]    // Launch state per cycle (Cold/Warm)
```

### Sequence – Per-Cycle Timing (in ms)

> **[v3 CHANGE]**: Sequence metrics giờ là **array per-cycle** thay vì scalar average.  
> Mỗi metric là `[cycle1_value, cycle2_value, cycle3_value]`.  
> Giá trị `0.0` nghĩa là metric không có data tại cycle đó.

```json
"sequence": {
  "App Execution Time": [954.705, 832.364, 1091.446],   // Per-cycle total launch time
  "Touch Down ~ Start Proc": [19.505, 17.556, 14.621],  // Touch down → process start
  "Start Proc": [1.038, 0.38, 0.307],                   // Process start duration
  "Start Proc ~ ActivityThreadMain": [50.1, 44.9, 48.2],
  "Activity Thread Main": [52.3, 50.1, 20.5],           // Main thread init
  "ActivityThreadMain ~ bindApplication": [3.6, 3.5, 3.7],
  "Bind Application": [58.1, 54.4, 56.8],               // App binding
  "bindApplication ~ activityStart": [1.1, 1.0, 1.2],
  "Activity Start": [284.225, 232.235, 340.741],         // Activity creation
  "activityStart ~ activityResume": [4.074, 2.741, 3.45],
  "Activity Resume": [56.204, 44.924, 49.878],           // Activity resume
  "ActivityResume ~ Choreographer": [5.249, 5.291, 6.447],
  "Choreographer": [53.386, 53.77, 64.887],              // First frame
  "Choreographer ~ ActivityIdle": [326.118, 311.945, 336.49],
  "ActivityIdle": [2.698, 2.617, 2.702],                 // System idle signal
  "ActivityIdle ~ Animating end": [0.0, 0.0, 0.0],      // Animation (0.0 = không có)

  // Thread states (per-cycle)
  "Running": [256.642, 252.052, 259.792],                // CPU running time
  "Runnable": [11.916, 10.79, 20.597],                   // Waiting for CPU
  "Uninterruptible Sleep": [284.361, 218.566, 336.684],  // Block I/O wait (D-state)
  "Sleeping": [244.449, 212.686, 331.662]                // Sleeping (S-state)
}
```

#### Cách tính Average từ per-cycle data
```python
values = sequence["Running"]            # [256.642, 252.052, 259.792]
non_zero = [v for v in values if v > 0] # Loại bỏ 0.0
avg = sum(non_zero) / len(non_zero)     # 256.162
```

> **Note**: Không phải tất cả apps đều có đầy đủ sections. Metrics chỉ xuất hiện nếu có ít nhất 1 cycle có giá trị > 0.

### Extend – Additional Context

> **[v3 CHANGE]**: `memory` và `uptime_minutes` giờ là **array per-cycle + *_avg field**.

```json
"extend": {
  "start_process_abnormal": [           // Per cycle: list of parallel-started processes
    [],                                 // Cycle 1: no abnormal
    ["id.gms.unstable"],               // Cycle 2: GMS started parallel
    []
  ],
  "loadapkassets": {                   // (Optional) Time spent loading APK assets (AVERAGE)
    "system_server": 62.971,           // Process name: avg time (ms)
    "system_ui": 104.846
  },
  "memory": {
    "MemFree_MB": [1800.5, 1200.3, 1500.2],       // Per-cycle MemFree (MB)
    "MemFree_MB_avg": 1500.33,                     // Average of non-zero values
    "MemAvailable_MB": [2400.1, 2300.5, 2350.8],   // Per-cycle MemAvailable (MB)
    "MemAvailable_MB_avg": 2350.47,
    "App_PSS_MB": [67.08, 67.2, 66.68],            // Per-cycle app PSS (MB)
    "App_PSS_MB_avg": 66.99,
    "Pageboostd_MB": [23.95, 23.95, 23.95],        // Per-cycle Pageboost (MB)
    "Pageboostd_MB_avg": 23.95
  },
  "abnormal": {
    "uptime_minutes": [7, 7, 7],                   // Per-cycle device uptime (minutes)
    "uptime_minutes_avg": 7.0,                     // Average
    "compiler": "speed-profile",                   // App compiler type
    "start_reasons": [                             // Start reasons (all cycles combined)
      "content provider",
      "content provider",
      "content provider"
    ]
  }
}
```

> **Note**: `memory` fields có thể không đầy đủ (thiếu MemFree_MB nếu không có memory file).
> Giá trị `0.0` trong per-cycle array = không có data tại cycle đó.

### Top Process Consume by Cycle
```json
"top_process_consume_by_cycle": [
  {
    "cycle": 1,
    "process": [
      {
        "name": "surfaceflinger",      // Process name (may be truncated)
        "dut": 711.34,                 // DUT CPU time (ms)
        "ref": 627.53,                 // REF CPU time (ms)
        "diff": 83.81                  // DUT - REF (ms)
      }
      // ... top 5 processes
    ]
  }
]
```

### Priority by Cycle
```json
"priority_by_cycle": [
  {
    "cycle": 1,
    "data": {
      "bindApplication": [
        { "priority": 120, "percentage": 100.0 }
      ],
      "activityStart": [
        { "priority": 110, "percentage": 100.0 }
      ],
      "activityResume": [
        { "priority": 110, "percentage": 100.0 }
      ],
      "Choreographer": [
        { "priority": 110, "percentage": 100.0 }
      ]
    }
  }
]
```

> **Priority values**: 110 = high priority (foreground), 120 = default, 130+ = lower priority.

### Frequency by Cycle
```json
"frequency_by_cycle": [
  {
    "cycle": 1,
    "data": {
      "bindApplication": [
        { "frequency": 2002, "percentage": 6.0 },
        { "frequency": 2400, "percentage": 94.0 }
      ],
      "activityStart": [
        { "frequency": 2400, "percentage": 100.0 }
      ]
    }
  }
]
```

> **Frequency values**: Đơn vị MHz. Higher = faster. Thường thấy: 2400 (max), 2002, 2288, etc.

### Block I/O by Cycle
```json
"block_io_by_cycle": [
  {
    "cycle": 1,
    "data": [
      {
        "name": "/data/app/SecCalculator_R/SecCalculator_R.apk",
        "val": 0                      // Block I/O duration (ms)
      }
    ]
  }
]
```

### Binder Transaction (averaged)
```json
"binder_transaction": {
  "duration_ms": 144.639,             // Total binder duration (ms)
  "count": 100                        // Number of binder calls
}
```

---

## Migration Notes (v2 → v3)

| Section | v2 (old) | v3 (new) |
|---------|----------|----------|
| `sequence.*` | Scalar average: `"Running": 233.1` | Array per-cycle: `"Running": [220, 235, 244]` |
| `extend.memory.*_MB` | Scalar average: `"MemFree_MB": 140.31` | Array + avg: `"MemFree_MB": [150, 130, 141]`, `"MemFree_MB_avg": 140.33` |
| `extend.abnormal.uptime_minutes` | Scalar average: `7.0` | Array + avg: `[7, 7, 7]`, `"uptime_minutes_avg": 7.0` |
| Other fields | No change | No change |

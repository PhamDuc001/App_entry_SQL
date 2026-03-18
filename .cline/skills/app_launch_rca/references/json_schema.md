# JSON Output Schema – execution_sql Pipeline

## File Types

| Type | Filename Pattern | Content |
|------|-----------------|---------|
| Failed apps only | `DUT_<model>_<ram>_<timestamp>.json` | Chỉ các app có performance issue |
| All apps | `DUT_all_apps_<timestamp>.json` | Tất cả apps (passed + failed) |

Cả DUT và REF đều có cùng schema, phân biệt qua field `type`.

---

## Root Level

```json
{
  "device_code": "8GB",        // RAM size hoặc device variant
  "version": "ZC1",            // Software version (build version)
  "timestamp": "2026-03-09T21:00:11.790734",
  "type": "DUT",               // "DUT" hoặc "REF"
  "apps_data": [...]           // Array of app entries
}
```

---

## Per App Entry (`apps_data[i]`)

```json
{
  "app": "calculator",         // App name (lowercase)
  "entry": { ... }             // Entry launch data (cold start)
}
```

> **Note**: Một số file có thể chứa thêm `"reentry"` cho warm start data, nhưng file failed apps thường chỉ chứa `"entry"`.

---

## Entry Object (`apps_data[i].entry`)

### State
```json
"State": ["Cold", "Cold", "Cold"]    // Launch state per cycle (Cold/Warm)
```

### Sequence – Timing Breakdown (averaged across cycles, in ms)
```json
"sequence": {
  "App Execution Time": 540.37,              // Tổng thời gian launch (Touch → end)
  "Touch Down ~ Start Proc": 12.323,         // Touch down → process start
  "Start Proc": 8.372,                       // Process start duration
  "Start Proc ~ ActivityThreadMain": 50.077,  // Gap
  "Activity Thread Main": 34.801,             // Main thread init
  "ActivityThreadMain ~ bindApplication": 3.603,
  "Bind Application": 58.13,                  // App binding
  "bindApplication ~ activityStart": 1.124,
  "Activity Start": 134.925,                  // Activity creation
  "activityStart ~ activityResume": 2.074,
  "Activity Resume": 37.247,                  // Activity resume
  "ActivityResume ~ Choreographer": 1.761,
  "Choreographer": 52.478,                    // First frame
  "Choreographer ~ ActivityIdle": 74.867,
  "ActivityIdle": 5.515,                      // System idle signal
  "ActivityIdle ~ Animating end": 63.073,     // Animation completion

  // Thread states (tổng thời gian trong mỗi state)
  "Running": 233.123,                 // CPU running time
  "Runnable": 17.785,                 // Waiting for CPU
  "Uninterruptible Sleep": 18.957,    // Block I/O wait (D-state)
  "Sleeping": 227.219                 // Sleeping (S-state)
}
```

> **Note**: Không phải tất cả apps đều có đầy đủ sections. Ví dụ: app Gallery không có `bindApplication` sections (warm launch) khi State = Cold nhưng không detect được bind.

### Extend – Additional Context

```json
"extend": {
  "start_process_abnormal": [          // Per cycle: list of parallel-started processes
    [],                                // Cycle 1: no abnormal
    ["id.gms.unstable"],              // Cycle 2: GMS started parallel
    []
  ],
  "loadapkassets": {                  // (Optional) Time spent loading APK assets
    "system_server": 62.971,          // Process name: time spent loading APK resources (ms)
    "system_ui": 104.846              // Multiple processes possible (though typically 1 app process)
  },
  "memory": {
    "MemFree_MB": 140.31,             // Free memory (MB)
    "MemAvailable_MB": 963.48,        // Available memory (MB)
    "App_PSS_MB": 28.32,              // App's Proportional Set Size (MB)
    "Pageboostd_MB": 0.15             // Pageboost prefetch amount (MB)
  },
  "abnormal": {
    "uptime_minutes": 7.0,            // Device uptime at test time
    "compiler": "verify",             // App compiler type: speed/speed-profile/verify
    "start_reasons": [                // (Optional) Process start reasons per cycle
      "content provider",
      "content provider"
    ]
  }
}
```

> **Note**: `memory` fields có thể không đầy đủ (thiếu MemFree_MB, MemAvailable_MB nếu không có memory file).

### Top Process Consume by Cycle
```json
"top_process_consume_by_cycle": [
  {
    "cycle": 1,
    "process": [
      {
        "name": "surfaceflinger",     // Process name (may be truncated)
        "dut": 711.34,                // DUT CPU time (ms)
        "ref": 627.53,                // REF CPU time (ms)
        "diff": 83.81                 // DUT - REF (ms)
      },
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

> **Priority values**: 110 = high priority (foreground), 120 = default, 130+ = lower priority. Lower number = higher priority.

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
      // activityResume, Choreographer...
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
        "val": 0                     // Block I/O duration (ms)
      }
    ]
  }
]
```

### Binder Transaction (averaged)
```json
"binder_transaction": {
  "duration_ms": 144.639,            // Total binder duration (ms)
  "count": 100                       // Number of binder calls
}
```

# Workflow Rules – 3-Flow Diagnostic System

Tài liệu này mô tả chi tiết 3 flows trong hệ thống diagnostic, dựa trên `AI_performance_root_workflow_v1_1/2/3.json`.

## Execution Mode

Tất cả flows chạy `exhaustive_sequential`: agent PHẢI chạy hết TẤT CẢ nodes trong mỗi flow, KHÔNG dừng sớm khi tìm thấy issue đầu tiên. Mỗi app phải chạy qua cả 3 flows.

---

## Flow 1: Initial Validation

**Mục đích**: Kiểm tra điều kiện test có hợp lệ không.

```
node_00_precondition_check
├── node_01_uptime_check
│   └── on_true → node_04_retest_condition
├── node_02_anr_fatal_check
│   └── on_true → node_05_anr_fatal_found + node_06_query_anr_history
└── node_03_touch_duration_check
    └── on_diff → node_07_touch_duration_issue
```

| Node | Type | Key | Threshold | Operator |
|------|------|-----|-----------|----------|
| uptime_check | check | `uptime_minutes` | 10 | DUT > 10 OR REF > 10 |
| anr_fatal_check | check | ANR, FATAL | - | exists |
| touch_duration_check | comparison | `touch_duration` | 10ms | DUT - REF > 10 |

---

## Flow 2: Core Performance State Analysis

**Mục đích**: Phân tích 4 trạng thái CPU chính và các sub-issues.

```
node_00_performance_check
├── node_01_running_check
│   └── on_true → node_05 (result) + node_06 (sub-group)
│       ├── node_10_compiler_check → node_15 (verify issue)
│       ├── node_12_frequency_check → node_17 (freq issue)
│       └── node_14_query_running_version
├── node_02_sleeping_check
│   └── on_true → node_07 (sub-group)
│       ├── node_19_binder_check → node_24 (binder issue)
│       └── node_23_query_sleeping
├── node_03_runnable_check
│   └── on_true → node_08_priority_check → node_34 (priority issue)
└── node_04_start_state_check
    └── on_true → node_09 (sub-group)
        ├── node_35_beks_check → node_38 (BEKS issue)
        ├── node_36_start_kill_check → node_39 (start/kill issue)
        └── node_37_query_start_state
```

| Node | Key | Threshold | Operator |
|------|-----|-----------|----------|
| running_check | `Running` | 50ms | DUT - REF > 50 |
| sleeping_check | `Sleeping` | 50ms | DUT - REF > 50 |
| runnable_check | `Runnable` | 50ms | DUT - REF > 50 |
| start_state_check | `State` | - | DUT==Cold AND REF==Warm |
| compiler_check | `compiler` | - | DUT==verify AND DUT≠REF |
| frequency_check | `frequency_by_cycle` | 15% | DUT high-freq% < REF by >15% |
| binder_check | `binder.count` | 10 | DUT - REF > 10 |
| priority_check | `priority_by_cycle` | 15% | DUT high-priority% < REF by >15% |

### Frequency Analysis Logic
1. Cho mỗi cycle, mỗi section (bindApplication, activityStart, activityResume, Choreographer)
2. Tìm **highest frequency** available
3. So sánh % thời gian ở highest frequency giữa DUT và REF
4. Flag nếu DUT chạy ít hơn >15% so với REF ở highest frequency

### Priority Analysis Logic
1. Cho mỗi cycle, mỗi section
2. Priority 110 = high (foreground), 120 = default, higher = lower priority
3. So sánh % thời gian ở **highest priority** (lowest number) giữa DUT và REF
4. Flag nếu DUT có ít high-priority time hơn >15% so với REF

---

## Flow 3: Resource Usage & Process Analysis

**Mục đích**: Phân tích tài nguyên (I/O, memory, processes).

```
node_00_resource_check
├── node_01_load_apk_asset_check
│   └── on_true → node_07_memory_check_detailed
├── node_02_block_io_check
│   └── on_true → node_06 (sub-group)
│       ├── node_07_memory_check_detailed → node_13 + node_14
│       ├── node_08_apk_size_check → node_15 + node_16
│       └── node_11_pageboost_check → node_21 (pageboost issue)
└── node_03_process_abnormal
    ├── node_23_parallel_process_check → node_26 + node_27
    ├── node_24_top_cpu_check → node_28 + node_29
    └── node_25_pss_check → node_30 + node_31
```

| Node | Key | Threshold | Operator |
|------|-----|-----------|----------|
| load_apk_asset_check | `loadApkAssets` | 30ms | DUT - REF > 30 |
| block_io_check | `Uninterruptible Sleep` | 30ms | DUT - REF > 30 |
| memory_check | `MemFree_MB`, `MemAvailable_MB` | 50MB | REF - DUT > 50 |
| pageboost_check | `Pageboostd_MB` | 10MB | REF - DUT > 10 |
| parallel_process | `start_process_abnormal` | - | has any process |
| top_cpu_check | `top_process_consume_by_cycle` | 300ms | process.diff > 300 |
| pss_check | `App_PSS_MB` | 50MB | DUT - REF > 50 |

---

## Node Types

| Type | Behavior |
|------|----------|
| `check_group` | Container – chạy tất cả child nodes |
| `check` | Boolean check → on_true hoặc skip |
| `comparison` | Numeric comparison → on_diff hoặc skip |
| `custom_check` | Complex logic (xem operator description) |
| `result` | Terminal – report problem + suggestion |
| `database_query` | Query history (optional, nếu có DB) |

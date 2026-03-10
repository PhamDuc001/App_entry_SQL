# Performance Analysis Report - 6GB vs BOS
**Session ID:** 6GB_20260310
**Timestamp:** 2026-03-10T08:40:28.171501

---

## gallery — FINDINGS DETECTED

### Flow 1: Initial Validation
- [node_01] uptime: DUT=7min REF=7min → PASS
- [node_02] ANR/FATAL: → PASS
- [node_03] touch_duration: → data not available

### Flow 2: Core Performance State
- [node_01] Running: DUT=321.284ms REF=190.282ms delta=131.002ms → ⚠ FINDING: "Suggest app team checking running time increase from app side"
  - [node_10] compiler: DUT=speed-profile REF=speed-profile → PASS
  - [node_12] frequency: DUT high-freq% (cycle1=100%, cycle3=87.45%) REF high-freq% (cycle1=87.97%, cycle3=100%) → PASS (delta < 15%)
  - [node_14] DB_QUERY: "Check new app version or fix" [gallery, version]
- [node_02] Sleeping: DUT=179.602ms REF=106.674ms delta=72.928ms → PASS (sub-nodes)
  - [node_19] binder count: DUT=82 REF=74 delta=8 → PASS
  - [node_23] DB_QUERY: "Check app fix history" [gallery, version]
- [node_03] Runnable: DUT=8.926ms REF=6.808ms delta=2.118ms → PASS
- [node_04] State: DUT=["Cold","Cold","Cold"] REF=["Cold","Cold"] → PASS

### Flow 3: Resource Usage
- [node_01] loadApkAssets: → data not exported yet
- [node_02] Uninterruptible Sleep: DUT=28.65ms REF=34.736ms delta=-6.086ms → PASS
- [node_23] parallel process: [] → PASS
- [node_24] top CPU per cycle:
  - Cycle 1 | ndroid.systemui | diff 368.13ms → ⚠ FINDING: "Cycle 1 | ndroid.systemui | diff 368.13ms"
  - Cycle 1 | droid.gallery3d | diff 346.6ms → ⚠ FINDING: "Cycle 1 | droid.gallery3d | diff 346.6ms"
  - Cycle 2 | [all processes] | diff 0.0ms → PASS
  - Cycle 3 | [all processes] | diff < 300ms → PASS
- [node_25] PSS: DUT=71.14MB REF=62.31MB delta=8.83MB → PASS

### Summary Findings for gallery
- [node_01] "Suggest app team checking running time increase from app side"
- [node_24] Cycle 1 | ndroid.systemui | diff 368.13ms → "Suggest SWPL check with owner of process"
- [node_24] Cycle 1 | droid.gallery3d | diff 346.6ms → "Suggest SWPL check with owner of process"

---

## note — FINDINGS DETECTED

### Flow 1: Initial Validation
- [node_01] uptime: DUT=8min REF=8min → PASS
- [node_02] ANR/FATAL: → PASS
- [node_03] touch_duration: → data not available

### Flow 2: Core Performance State
- [node_01] Running: DUT=267.073ms REF=147.089ms delta=119.984ms → ⚠ FINDING: "Suggest app team checking running time increase from app side"
  - [node_10] compiler: DUT=speed-profile REF=speed-profile → PASS
  - [node_12] frequency: DUT high-freq% (cycle1=94.37%, cycle3=97.83%) REF high-freq% (cycle2=87.97%, cycle3=94.8%) → PASS (delta < 15%)
  - [node_14] DB_QUERY: "Check new app version or fix" [note, version]
- [node_02] Sleeping: DUT=120.082ms REF=153.983ms delta=-33.901ms → PASS
- [node_03] Runnable: DUT=16.146ms REF=8.419ms delta=7.727ms → PASS
- [node_04] State: DUT=["Cold","Cold","Cold"] REF=["Cold","Cold"] → PASS

### Flow 3: Resource Usage
- [node_01] loadApkAssets: → data not exported yet
- [node_02] Uninterruptible Sleep: DUT=141.39ms REF=30.687ms delta=110.703ms → ⚠ PASS (sub-nodes)
  - [node_07] MemFree/MemAvail: REF=351.02 DUT=611.93 delta=260.91MB → PASS
  - [node_08] apk_size: → data not exported yet
  - [node_11] Pageboostd: REF=77.0 DUT=29.73 delta=47.27MB → PASS
- [node_23] parallel process: [] → PASS
- [node_24] top CPU per cycle:
  - Cycle 1 | droid.app.notes | diff 611.61ms → ⚠ FINDING: "Cycle 1 | droid.app.notes | diff 611.61ms"
  - Cycle 1 | surfaceflinger | diff 435.72ms → ⚠ FINDING: "Cycle 1 | surfaceflinger | diff 435.72ms"
  - Cycle 1 | system_server | diff 433.22ms → ⚠ FINDING: "Cycle 1 | system_server | diff 433.22ms"
  - Cycle 2 | droid.app.notes | diff 335.13ms → ⚠ FINDING: "Cycle 2 | droid.app.notes | diff 335.13ms"
  - Cycle 3 | droid.app.notes | diff 302.26ms → ⚠ FINDING: "Cycle 3 | droid.app.notes | diff 302.26ms"
- [node_25] PSS: DUT=166.6MB REF=143.1MB delta=23.5MB → PASS

### Summary Findings for note
- [node_01] "Suggest app team checking running time increase from app side"
- [node_24] Cycle 1 | droid.app.notes | diff 611.61ms → "Suggest SWPL check with owner of process"
- [node_24] Cycle 1 | surfaceflinger | diff 435.72ms → "Suggest SWPL check with owner of process"
- [node_24] Cycle 1 | system_server | diff 433.22ms → "Suggest SWPL check with owner of process"
- [node_24] Cycle 2 | droid.app.notes | diff 335.13ms → "Suggest SWPL check with owner of process"
- [node_24] Cycle 3 | droid.app.notes | diff 302.26ms → "Suggest SWPL check with owner of process"

---

## Overall Summary
- Total findings detected: 9
- Apps analyzed: 2 (gallery, note)
- Issues found: Running time increase (2 apps), top CPU process consumption (2 apps)
- Critical findings: note app shows consistent high diff across all cycles for droid.app.notes process
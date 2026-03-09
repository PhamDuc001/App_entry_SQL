# Domain Glossary — Android App Launch Performance

## Device Roles
- **DUT** (Device Under Test): Device being tested. May be multiple versions: DUT1, DUT2, ...
- **REF** (Reference): Baseline device with stable build. Primary comparison target.
- **Diff convention**: DUT - REF → Positive = DUT slower/worse, Negative = DUT faster/better
- **Cross-version normalization**: `delta = (DUT2 - REF2) - (DUT1 - REF1)` — removes environmental variance

## Launch Types
| Type | State value | Traces | Key signals |
|------|-------------|--------|-------------|
| Cold | "Cold" | Odd (1,3,5...) | Has BindApplication, StartProc |
| Warm | "Warm" | Even (2,4,6...) | Has TouchDuration, no BindApplication |

**Cycle index**: `(occurrence - 1) // 2`  
Traces 1+2 → Cycle 0 | Traces 3+4 → Cycle 1

## Metric Thresholds

| Metric | Workflow Flag Threshold | Severity |
|--------|------------------------|----------|
| App Execution Time diff | > 10 ms | Medium → Critical by magnitude |
| Bind Application diff | > 10 ms | Medium |
| Running diff | > 50 ms | Medium |
| Sleeping/Runnable diff | > 50 ms | Medium |
| Uninterruptible Sleep diff | > 30 ms | Medium (I/O bottleneck signal) |
| Touch Duration diff | > 10 ms | Medium |
| Block I/O diff | > 50 ms | Medium |
| LoadApkAssets diff | > 30 ms | Medium |
| MemFree/MemAvailable drop | > 50 MB | Medium |
| Pageboostd drop | > 10 MB | Medium |
| PSS increase | > 50 MB | Medium |
| Binder count diff | > 10 | Medium |
| Top CPU process diff | > 300 ms per cycle | High |
| Crashes | > 0 | Critical |
| Uptime | > 10 minutes | Invalid test condition |

## Cold-Only Keys (empty/N/A for Warm launches)
- Touch Down ~ Start Proc
- Start Proc
- Start Proc ~ ActivityThreadMain
- Activity Thread Main
- ActivityThreadMain ~ bindApplication
- Bind Application
- bindApplication ~ activityStart

## Warm-Only Keys (empty/N/A for Cold launches)
- Touch Duration
- Touch Up ~ Activity Start

## Compiler Types (ranked best→worst for Cold launch)
1. `speed` — Full AOT, fastest Cold launch
2. `speed-profile` — Profile-guided AOT, good balance
3. `verify` — JIT only, slowest Cold launch → flag as issue

## Priority Data Interpretation
- Priority values: lower number = higher priority (Linux convention)
- Priority 100 = real-time | 120 = normal foreground | 140 = background
- Flag: DUT spends >15% more time at priority ≥ 140 than REF in the same phase

## Frequency Data Interpretation
- Higher frequency = more CPU power = faster execution
- Flag: DUT spends >15% less time at highest available frequency than REF in same phase

## Uptime Rule
- uptime_minutes > 10 → test condition invalid for either DUT or REF
- Reason: system caches warm up over time, affecting launch times

## Start/Kill Reason Analysis
Normal start reason: `launcher` (user tap)
Abnormal: `broadcast`, `content provider`, `service` before the test launch
Kill reasons present = app was killed before test → may cause unexpected Cold start
Rule: `DUT.start_reason.length != REF.start_reason.length` = suspicious

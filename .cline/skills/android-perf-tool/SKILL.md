---
name: android-perf-tool
description: >
  Use this skill whenever the task involves developing, debugging, extending, or reviewing
  the Android App Performance Root Diagnostic tool — including editing Python extraction code
  (sql_query.py, execution_sql.py), designing or modifying diagnostic workflow JSON files,
  tracing data flow from .log traces through to Excel/JSON output, or diagnosing why a metric
  is missing, wrong, or inconsistent. Trigger on any mention of: DUT, REF, Cold/Warm launch,
  trace processor, perfetto, execution time metrics, ANR/FATAL, binder, PSS, pageboost,
  block I/O, priority statics, frequency statics, loadApkAssets, workflow nodes, or
  any of the target apps (camera, clock, gallery, etc.).
---

# android-perf-tool

This tool extracts, compares, and diagnoses Android app launch performance by processing
Perfetto `.log` traces from two devices: **DUT** (Device Under Test) and **REF** (Reference).

## Usage

Whenever the task involves developing, debugging, extending, or reviewing
the Android App Performance Root Diagnostic tool — including editing Python extraction code
(sql_query.py, execution_sql.py), designing or modifying diagnostic workflow JSON files,
tracing data flow from .log traces through to Excel/JSON output, or diagnosing why a metric
is missing, wrong, or inconsistent. Trigger on any mention of: DUT, REF, Cold/Warm launch,
trace processor, perfetto, execution time metrics, ANR/FATAL, binder, PSS, pageboost,
block I/O, priority statics, frequency statics, loadApkAssets, workflow nodes, or
any of the target apps (camera, clock, gallery, etc.).

**Two-file architecture:**
| File | Role |
|------|------|
| `sql_query.py` | Extraction layer — all Perfetto SQL queries, `analyze_trace()` |
| `execution_sql.py` | Orchestration + output — batch processing, Excel/JSON generation |

**Three diagnostic workflow JSONs** (consumed by an AI agent, not by these Python files):
- `Flow 1` — Initial validation (uptime, ANR/FATAL, touch duration)
- `Flow 2` — Core performance state (Running, Sleeping, Runnable, start state)
- `Flow 3` — Resource usage (Block I/O, memory, process anomalies)

---

## Task Routing — Read This First

**Before writing any code or workflow**, identify which reference to load:

| Task type | Load this reference |
|-----------|-------------------|
| Adding/editing a metric, query, or Excel section | `references/codebase-guide.md` |
| Debugging wrong/missing data in output | `references/codebase-guide.md` → Data Flow section |
| Designing or editing a workflow JSON node | `references/workflow-design.md` |
| Reviewing diagnostic logic / thresholds | `references/workflow-design.md` + domain glossary below |
| Understanding what a metric means | Domain Glossary below (no extra file needed) |

---

## Domain Glossary (Always in Context)

**DUT / REF** — Two parallel device captures compared side-by-side. DUT is the device being
tested; REF is the baseline. All comparisons are `DUT - REF` (positive = DUT slower/worse).

**Cold launch** — App starts from scratch: `bindApplication` → `activityStart` → `activityResume`
→ `Choreographer` → `ActivityIdle`. Has `Touch Down ~ Start Proc`, `Start Proc`, `BindApplication`.

**Warm launch** — App already in memory, resumes: skips bindApplication block.
Has `Touch Duration`, `Touch Up ~ Activity Start`.

**Entry / Reentry** — Within each app, odd-numbered traces (1,3,5…) = Entry (1st launch),
even-numbered (2,4,6…) = Reentry (2nd launch). `cycle_index = (occurrence - 1) // 2`.

**State** — List of per-cycle launch states within a section (entry or reentry).
e.g. `entry.State = ["Cold","Cold","Cold"]` = all 3 entry cycles were Cold launches.
State is NOT derived from the section name — it reflects actual memory state of the
app process at the time of each cycle. Both `entry` and `reentry` sections can contain
Cold or Warm states independently.

**Cycle** — One Entry+Reentry pair. Cycle 0 = traces 1+2, Cycle 1 = traces 3+4, etc.

**end_ts_variants** — Some apps have multiple possible "end" events (activityIdle, animating,
startPreviewRequest). The tool picks the **common type with the largest average value** across
DUT and REF, ensuring apples-to-apples comparison.

**Key metric groups:**
- **Timeline** — `App Execution Time`, `Bind Application`, `Activity Start`, `Activity Resume`,
  `Choreographer`, `ActivityIdle` (and transitions between them)
- **Thread states** — `Running`, `Runnable`, `Uninterruptible Sleep`, `Sleeping` (in ms)
- **Extended** — `MemFree_MB`, `MemAvailable_MB`, `App_PSS_MB`, `Pageboostd_MB`,
  `Binder_Transaction_Data`, `Block_IO_Data`, `LoadApkAsset_Data`
- **Classification** — `Priority_Data` (per thread priority × frequency), `CPU_Process_Data`,
  `CPU_Thread_Data`, `Abnormal_Process_Data`

**COLD_ONLY_KEYS** — Metrics that only exist in Cold launches. Writing these for a Warm cycle
must be skipped (masked to empty). Set defined in `execution_sql.py`.

**WARM_ONLY_KEYS** — `Touch Duration`, `Touch Up ~ Activity Start`. Skip for Cold cycles.

**Diff coloring thresholds:**
- Most metrics: red if `diff > 10ms`, green if `diff < -10ms`
- `Uninterruptible Sleep`: threshold is 30ms
- Block I/O / LoadApkAssets / CPU: threshold is 50ms

---

## Non-Negotiable Invariants

These must never be violated when modifying the codebase:

1. **`cycle_index = (occurrence - 1) // 2`** — Never deviate from this formula.
2. **`_process_single_trace_worker` must return a 5-tuple** `(app_name, occurrence, category, metrics, filename)` even on error (metrics=None).
3. **`Precomputed_Extend_Data`** is the only channel for dumpstate-derived data (PSS, uptime, memory, compiler, start/kill reasons). Never read bugreport files inside `analyze_trace()`.
4. **`select_common_end_ts_type()`** must be called before any DUT/REF comparison in Excel output. Never compare raw cycles with mismatched end_ts types.
5. **Masking logic** (COLD_ONLY_KEYS / WARM_ONLY_KEYS) must be applied in both `create_sheet()` and `calculate_metrics_for_app()`. Adding a new state-specific metric requires updating both places.
6. **Workflow JSON nodes** with `type: result` must never have a `next` field. Terminal nodes only.
7. **All `database_query` nodes** must run in parallel with their sibling result nodes — never block diagnosis output.

---

## When Debugging

Follow this sequence before modifying any code:

1. **Is the metric missing entirely?** → Check if `analyze_trace()` in `sql_query.py` populates it
2. **Is the value 0.0 or blank?** → Check masking logic (wrong launch type?) and `write_value_or_empty()` (0.0 renders as empty by design)
3. **Is DUT/REF mismatched?** → Check `select_common_end_ts_type()` return value; "mismatch" means no common end event was found
4. **Is a cycle showing None?** → Worker failed silently; check `_process_single_trace_worker` error handling
5. **Is the Excel column offset wrong?** → Recalculate: `dut_avg_col = 1 + max_cycles`, `ref_avg_col = dut_avg_col + 1 + max_cycles`, `diff_col = ref_avg_col + 1`

---

*For code patterns, data flow, and adding new metrics → read `references/codebase-guide.md`*
*For workflow JSON design rules and node templates → read `references/workflow-design.md`*

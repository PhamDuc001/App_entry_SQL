# Trace Analysis Guide

## Deep Dive Methodology

### Phase 1: Identify the Bottleneck Section
1. Compare each section's duration: DUT vs REF
2. Calculate % contribution to total execution time
3. Rank sections by absolute diff (largest first)
4. Focus on top 2-3 contributors

### Phase 2: Analyze Thread State Distribution
For the bottleneck section identified:
1. **Running high** → CPU bound → check frequency, compiler
2. **Sleeping high** → Waiting for something → check binder, lock
3. **Runnable high** → CPU contention → check priority, other processes
4. **D-state high** → I/O bound → check memory, pageboost, block I/O

### Phase 3: Cross-Reference Resources
| If | Then Check |
|-----|-----------|
| Running ↑ in bindApplication | compiler type, apk complexity |
| Running ↑ in activityStart | app code change, new features |
| Sleeping ↑ | binder transactions, content provider queries |
| Runnable ↑ | thread priority, competing processes |
| D-state ↑ | MemFree, Pageboost, block I/O libraries |

### Phase 4: Cycle Variance Analysis
1. Calculate standard deviation across cycles
2. High variance (CV > 30%) → inconsistent issue (intermittent)
3. Low variance (CV < 10%) → systematic issue (repeatable)
4. One outlier cycle → check process interference at that cycle

## Section Reference

| Section | What Happens | Common Issues |
|---------|-------------|---------------|
| Touch → Start Proc | System receives touch, routes to AMS | Touch driver delay, system_server busy |
| Start Proc | AMS calls Process.start() | Zygote fork delay |
| ActivityThreadMain | App's main thread starts | Class loading, static init |
| bindApplication | App binds to runtime | DEX loading, JIT/AOT, providers |
| activityStart | onCreate + onStart | Layout inflation, data loading |
| activityResume | onResume | View restoration, animations |
| Choreographer | First frame rendering | Drawing complexity, GPU |
| → ActivityIdle | Post-frame system notification | System processing |

## Frequency Analysis Tips

- **2400 MHz = max**: App should spend >90% at max during launch
- **Mixed frequencies**: Scheduler didn't boost enough or cluster migration
- **Section-specific**: Frequency drop at specific section → governor not reacting to that workload pattern
- **Compare DUT vs REF per section**: If REF also has lower frequency at same section, it's expected

## Priority Analysis Tips

- **110 = foreground**: App main thread should always be at 110 during visible activity
- **120 at bindApplication**: Normal – app not yet visible
- **120 at activityStart/Resume/Choreographer**: Abnormal – should be 110
- **Mixed (e.g., 98.7% @110, 1.3% @120)**: Brief scheduling delay, usually acceptable

# Insights & Patterns

> Agent append vào đây khi phát hiện pattern mới.
> Ghi rõ [MODEL_VARIANT] ở đầu mỗi insight.

---

## Cross-Model Patterns
<!-- Pattern xuất hiện ở NHIỀU model+variant -->

---

## A266B_4GB
### Recurring Issues
### Performance Trend

## A266B_6GB
### Recurring Issues
- **Running time regression**: Both gallery (+81.6ms) and note (+80.6ms) show significant Running time increases vs REF, requiring app-side investigation
- **Binder transactions**: gallery app shows 23 additional binder calls vs REF, indicating potential IPC overhead
- **System Server CPU consumption**: Multiple cycles show system_server exceeding 300ms diff threshold (gallery: 508.95ms, 687.05ms, 445.93ms; note: 425.38ms)
- **Pageboostd regression**: note app shows 41.24MB delta (REF-DUT), suggesting pageboost operation issues
- **Uninterruptible Sleep**: note app shows significant increase (+87.4ms), requiring memory investigation

### Performance Trend
**Session BOS_20260310 (Initial)**
- Apps analyzed: gallery, note
- Total findings: 13 regressions
- Key patterns: High system_server CPU consumption across both apps, Running time regressions, Pageboostd issues for note app
- State consistency: All launches Cold (DUT 3 cycles, REF 2 cycles)
- Compiler: Both using speed-profile (good)
- Memory: PSS increases within acceptable range (gallery +13.55MB, note +32.54MB)

**Session 6GB_20260310**
- Apps analyzed: gallery, note
- Total findings: 9 regressions
- Running time regression persists: gallery +131ms, note +120ms (slightly improved from previous session)
- Key pattern shift: system_server CPU consumption reduced, but app-specific processes show high diff
- **gallery**: ndroid.systemui (368ms), droid.gallery3d (346ms) in Cycle 1 only
- **note**: Consistent high droid.app.notes consumption across all cycles (611ms, 335ms, 302ms) - indicates chronic issue
- Additional system processes: surfaceflinger (435ms), system_server (433ms) in Cycle 1 for note
- Compiler consistency: Both using speed-profile (good)
- Memory: PSS increases stable (gallery +8.83MB, note +23.5MB)
- Session comparison: 9 findings vs 13 in previous session (improvement trend)

## A165F_4GB
### Recurring Issues
### Performance Trend

## A075F_4GB
### Recurring Issues
### Performance Trend

---
<!-- Thêm model mới: append ## [MODEL]_[VARIANT] vào đây -->

# Performance Report Template

## Quick Reference

### Report Sections (in order)

1. **Header** – Model, DUT/REF info, test date
2. **Executive Summary** – Total apps, pass/fail counts, overall assessment
3. **App Results Overview** – Summary table with status icons
4. **Detailed Findings** – Per failed/warning app (timing, issues, recommendations)
5. **Environment Info** – Version, uptime, etc.
6. **Action Items Summary** – Consolidated action items with priority

### Status Icons

| Icon | Meaning | When |
|------|---------|------|
| ✅ | Pass | Within acceptable range |
| ⚠️ | Warning | Marginal – needs monitoring |
| 🔴 | Fail | Significant regression |
| ⚪ | No baseline | REF data missing |
| 📈 | Trending up | Metric increasing over versions |
| 📉 | Trending down | Metric decreasing (improvement for time metrics) |
| ➡️ | Stable | No significant change |

### Severity Levels for Action Items

| Priority | Criteria |
|----------|----------|
| **Critical** | ANR/FATAL, uptime invalid |
| **High** | Execution diff > 200ms, D-state > 100ms |
| **Medium** | Execution diff 100-200ms, Running/Sleeping > 50ms |
| **Low** | Compiler optimization, minor diff |

### Formatting Rules

- Use **bold** for abnormal values in tables
- Show diff as `+N.N ms (+X.X%)` for increases
- Show diff as `-N.N ms (-X.X%)` for decreases
- Round all values to 1 decimal place
- Use horizontal rules `---` between app sections
- Include cycle count (e.g., "Cold x3" meaning 3 Cold launch cycles)

### Example: Minimal Report (1 app pass)

```markdown
# App Launch Performance Report

| Field | Value |
|-------|-------|
| **DUT** | 8GB / ZC1 |
| **REF** | BOS / ZB1 |
| **Test Date** | 2026-03-09 |

## Executive Summary
- **Total Apps Tested**: 1
- **Pass**: 1 ✅
- Overall: No performance issues detected.

## App Results
| App | DUT | REF | Diff | Status |
|-----|-----|-----|------|--------|
| clock | 320.5 ms | 315.2 ms | +5.3 ms (+1.7%) | ✅ |

## Action Items
None.
```

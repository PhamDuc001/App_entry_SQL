---
name: p4-blame-analysis
description: Trace lịch sử thay đổi trên Perforce (P4) để tìm CL gây ra regression hoặc
  config mismatch trong Samsung Mobile / Android Kernel development. Dùng skill này
  khi user muốn biết ai/khi nào/CL nào đã thay đổi một file, sysfs path, kernel module,
  system property, hoặc config; khi cần bisect regression giữa 2 build; khi cần
  cross-ref CL với PLM ticket. Trigger khi thấy: p4, perforce, CL, changelist,
  filelog, annotate, blame, "ai thay đổi", "CL nào", "build nào introduce",
  "regression từ khi nào", depot path (//depot/, //...).
---

# p4-blame-analysis

Skill điều tra lịch sử thay đổi trên Perforce cho Samsung Mobile kernel/platform development.

## Workflow tổng quan

```
Input (file path / config / module name)
  → Bước 1: Resolve depot path
  → Bước 2: Chọn investigation strategy
  → Bước 3: Build p4 command sequence
  → Bước 4: Phân tích output
  → Bước 5: Cross-ref PLM / GitHub nếu cần
  → Output: Timeline + suspect CL + recommended action
```

---

## Bước 1 — Resolve depot path từ input

User có thể đưa vào nhiều dạng input khác nhau:

| Input dạng | Ví dụ | Cách resolve |
|------------|-------|--------------|
| Depot path đầy đủ | `//depot/kernel/drivers/input/...` | Dùng trực tiếp |
| Local workspace path | `D:\P4\kernel\drivers\input\booster.c` | Map sang depot path qua `p4 where` |
| Sysfs path | `/sys/class/input_booster/touch/head` | Tìm source file implement sysfs node này |
| Property name | `sys.perf.tbooster` | Tìm file set property này (init.rc, build.prop) |
| Module name | `input_booster_lkm.ko` | Tìm Android.mk / Kbuild source |
| Feature name | `TouchBooster`, `EMS`, `AAL` | Tìm theo pattern trong depot |

**Khi input là sysfs/property/feature** (không phải file path), hỏi user confirm trước khi search:
```
Bạn muốn trace:
  [a] File implement sysfs node này (C source)
  [b] Config file (config.xml, init.rc, build.prop)
  [c] Cả hai
```

---

## Bước 2 — Chọn investigation strategy

### Strategy A: "Ai thay đổi gần nhất?" (blame)
Dùng khi: mismatch mới xuất hiện, build N-1 OK nhưng build N fail.

```bash
# Xem lịch sử đầy đủ của file
p4 filelog -l //depot/path/to/file

# Blame từng dòng (xem CL nào viết dòng nào)
p4 annotate -c //depot/path/to/file

# Xem diff của CL cụ thể
p4 describe -du {CL_number}
```

### Strategy B: "Thay đổi gì giữa 2 build?" (range diff)
Dùng khi: có CL number của 2 build (từ BinaryInfo sheet — `ro.build.changelist`).

```bash
# List tất cả CL trong range
p4 changes //depot/path/...@{CL_start},{CL_end}

# Filter theo specific path (ví dụ chỉ kernel/ems)
p4 changes //depot/kernel/drivers/ems/...@{CL_start},{CL_end}

# Diff toàn bộ path giữa 2 CL
p4 diff2 //depot/path/...@{CL_start} //depot/path/...@{CL_end}
```

### Strategy C: "CL này thay đổi gì?" (CL inspection)
Dùng khi: có CL number cụ thể từ PLM ticket hoặc build note.

```bash
# Xem full diff của một CL
p4 describe -du {CL_number}

# Xem chỉ file list (không có diff)
p4 describe -s {CL_number}
```

### Strategy D: "Feature X được thêm vào từ bao giờ?" (origin trace)
Dùng khi: cần hiểu history của một feature qua nhiều bản OneUI.

```bash
# Tìm CL đầu tiên mention keyword
p4 changes -l //depot/...@1,now | grep -i "{keyword}"

# Trace file qua integrate/branch
p4 filelog -i //depot/path/to/file
```

---

## Bước 3 — Command sequences theo scenario thực tế

### Scenario: Tìm nguyên nhân mismatch `sys.perf.tbooster = false` trên DUT

```bash
# 1. Tìm file set property này
p4 grep -r "sys.perf.tbooster" //depot/...

# 2. Xem lịch sử của file đó
p4 filelog -l //depot/{found_file}

# 3. Diff với build REF (dùng CL từ BinaryInfo)
p4 diff2 //depot/{found_file}@{REF_CL} //depot/{found_file}@{DUT_CL}
```

### Scenario: Bisect regression giữa build cũ (CL_A) và build mới (CL_B)

```bash
# 1. List tất cả CL trong range cho module liên quan
p4 changes -l //depot/kernel/drivers/input/...@{CL_A},{CL_B}
p4 changes -l //depot/vendor/etc/...@{CL_A},{CL_B}

# 2. Filter CL có liên quan đến performance keywords
# (Tìm CL mention: booster, governor, ems, perf, sys.perf)
p4 changes -l //depot/...@{CL_A},{CL_B} | grep -iE "booster|governor|ems|sys\.perf"

# 3. Inspect suspect CL
p4 describe -du {suspect_CL}
```

### Scenario: Review CL trước khi submit (impact check)

```bash
# Xem pending CL của mình
p4 describe -du {my_pending_CL}

# Check xem file nào đã được người khác sửa gần đây
p4 filelog -m 5 //depot/{my_file}

# Check conflicts tiềm năng
p4 resolve -n
```

---

## Bước 4 — Phân tích output

### Parse `p4 filelog` output

```
//depot/path/file#N  change {CL} {action} on {date} by {user}@{client}
    '{CL description}'
```

Khi phân tích, Claude sẽ:
1. **Identify suspect CL**: CL gần nhất trước thời điểm regression
2. **Flag keywords trong description**: fix, revert, disable, remove, update config
3. **Detect revert pattern**: nếu CL description có "revert CL {X}" → trace CL X
4. **Extract PLM ticket ID**: format `{PROJECT}-{NUMBER}` trong description → cross-ref

### Parse `p4 describe` output

Từ diff output, Claude sẽ:
- Tóm tắt thay đổi bằng ngôn ngữ tự nhiên
- Map thay đổi sang checklist category (Governor/Property/KernelConfig/...)
- Đánh giá performance impact (dùng knowledge từ `perf-checklist-analyst`)
- List file bị affected theo priority

---

## Bước 5 — Cross-reference

### Với PLM (nếu có MCP PLM)
- Extract ticket ID từ CL description
- Query ticket status, assignee, reproduce steps
- Link timeline: CL date ↔ ticket creation date

### Với GitHub (nếu có MCP GitHub)
- Check nếu CL được mirror sang GitHub
- Xem PR/commit tương ứng
- Check review comments

### Với `perf-checklist-analyst`
- Map files bị thay đổi trong CL sang checklist items
- Predict mismatch nào cần re-verify sau CL này

---

## Output format chuẩn

### Short answer (1 file, 1 câu hỏi cụ thể)
```
File: {depot_path}
Last change: CL {number} on {date} by {user}
Description: "{tóm tắt}"
Impact: {performance impact nếu có}
PLM ref: {ticket nếu extract được}

Suggested verify:
  p4 describe -du {CL_number}
```

### Full investigation report (regression bisect)
```
## P4 Investigation Report
Target: {file/module/feature}
Range: CL {A} → CL {B} ({date_A} → {date_B})

### Timeline
| CL | Date | Author | Summary | Suspect? |
|----|------|--------|---------|----------|
| ... | ... | ... | ... | 🔴/🟡/⚪ |

### Suspect CLs (ordered by likelihood)
1. 🔴 CL {X} — {lý do suspect}
   Files: {danh sách}
   Verify: p4 describe -du {X}

### Recommended bisect order
1. Test với CL {X} reverted
2. If still fails → test CL {Y}
...

### Next steps
- [ ] {action cụ thể}
```

---

## Tips & Samsung-specific patterns

### Depot path patterns hay gặp (tham khảo, user confirm)
```
Kernel drivers:    //depot/kernel/drivers/...
EMS/Governor:      //depot/kernel/drivers/soc/samsung/ems/...
Input booster:     //depot/kernel/drivers/input/...
Vendor configs:    //depot/vendor/etc/...
Init scripts:      //depot/device/{model}/...
System properties: //depot/device/{model}/system.prop hoặc build.prop
Performance HAL:   //depot/vendor/samsung/hardware/perfhal/...
```

### CL description patterns suspect
- `disable`, `remove`, `revert` → khả năng cao gây regression
- `fix for {other feature}` → side effect
- `update default value` → config thay đổi
- `WIP`, `temp`, `hack` → không stable
- Không có PLM ticket reference → change chưa được track

### Workflow kết hợp với checklist
Khi có BinaryInfo từ Excel checklist:
- `ro.build.changelist` của DUT = CL_DUT
- `ro.build.changelist` của REF = CL_REF
→ Dùng range `@{CL_REF},{CL_DUT}` để bisect tất cả thay đổi giữa 2 build

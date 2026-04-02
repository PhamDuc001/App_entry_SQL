---
description: E2E Performance Test Analysis – Run rule screening + AI Skill analysis
---

# Performance Test Analysis Pipeline

Full pipeline từ JSON output → Rule screening → AI deep analysis → Report.

> **Prerequisite**: Đã chạy `execution_sql.py` và có DUT + REF JSON files trong Output folder.

// turbo-all

## Step 1: Xác định file paths

Tìm DUT và REF JSON files trong Output folder:

```
# Ví dụ paths:
DUT: D:\FE\Data\<model>\Output\DUT_<model>_<ram>_<timestamp>.json
REF: D:\FE\Data\<model>\Output\REF_<model>_<ram>_<timestamp>.json
```

## Step 2: Chạy Rule Screening

```powershell
python D:\Tools\CheckList\Bringup\Plan_convert_SQL\.cline\skills\app_launch_rca\scripts\rule_screening.py --dut "<DUT_JSON_PATH>" --ref "<REF_JSON_PATH>"
```

Output: `screening_result.json` sẽ được tạo cùng folder với DUT file.

Kết quả sẽ show summary trên terminal:
- ✅ PASS: Apps không có vấn đề
- ❌ FAIL: Apps cần AI phân tích sâu
- ⚠️ INVALID: Test condition không hợp lệ (cần re-test)

## Step 3: AI Deep Analysis (Skill)

Nếu có apps FAIL, dùng prompt:

```
Đọc skill app_launch_rca.skill, load screening result và data:
- Screening: <path>/screening_result.json
- DUT: <path>/DUT_*.json
- REF: <path>/REF_*.json

Phân tích sâu các apps FAIL, tìm root cause và suggest team routing.
```

## Step 4: Generate Report (Skill)

```
Dùng auto_report.skill tạo performance report từ:
- Screening: <path>/screening_result.json
- DUT: <path>/DUT_*.json
- REF: <path>/REF_*.json
```

## Step 5: Review & Distribute

- PE review AI output → approve/modify
- Upload report lên shared drive
- Gửi action items đến teams được routing
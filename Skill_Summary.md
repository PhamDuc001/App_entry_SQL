# Tóm tắt về Cline Skills

> Tài liệu tổng hợp về Skills, Workflow, Rule và Script trong Cline AI Agent

---

## Mục lục

1. [Giới thiệu về Skills](#1-giới-thiệu-về-skills)
2. [Rule vs Workflow vs Skill](#2-rule-vs-workflow-vs-skill)
3. [Workflow vs Skill - Sự khác biệt](#3-workflow-vs-skill---sự-khác-biệt)
4. [Script trong Skill](#4-script-trong-skill)
5. [Important Rules trong Skill](#5-important-rules-trong-skill)
6. [Kết hợp cả 3 trong thực tế](#6-kết-hợp-cả-3-trong-thực-tế)
7. [FAQ](#7-faq)

---

## 1. Giới thiệu về Skills

### 1.1 Khái niệm

Skills là **bộ hướng dẫn mô-đun** (modular instruction sets) mở rộng khả năng của Cline AI Agent cho các tác vụ cụ thể. Mỗi skill đóng gói hướng dẫn chi tiết, quy trình làm việc, và tài nguyên bổ sung mà Agent chỉ tải khi cần thiết.

### 1.2 Ví von dễ hình dung

```
Skill = "Sách hướng dẫn sử dụng chuyên gia"
- Chứa kiến thức chuyên sâu về 1 domain
- Agent đọc skill → có đủ kiến thức → làm việc chuyên môn
- Skill "ngủ đông" cho đến khi được kích hoạt
```

**So sánh:**
- **Rule** = "Sách luật" - Bộ điều kiện if/then cố định
- **Workflow** = "Công thức nấu ăn" - Chuỗi các bước theo thứ tự
- **Skill** = "Đầu bếp biết nấu" - Bộ kiến thức + kinh nghiệm

### 1.3 Cách hoạt động (Progressive Loading)

| Level | Khi nào được tải | Token Cost | Nội dung |
|-------|------------------|------------|----------|
| **Metadata** | Luôn luôn (khi khởi động) | ~100 tokens/skill | Tên và mô tả từ YAML frontmatter |
| **Instructions** | Khi skill được kích hoạt | Dưới 5k tokens | Nội dung SKILL.md với hướng dẫn |
| **Resources** | Khi cần thiết | Gần như không giới hạn | Files được truy cập qua read_file |

**Quy trình:**
```
User gửi tin nhắn
    ↓
Cline thấy danh sách skills có sẵn
    ↓
Nếu yêu cầu khớp với description → Kích hoạt skill
    ↓
Agent đọc SKILL.md → Có kiến thức domain
    ↓
Agent suy luận → Trả lời câu hỏi / Thực hiện tác vụ
```

### 1.4 Cấu trúc Skill

```
my-skill/
├── SKILL.md          # Bắt buộc: Hướng dẫn chính
├── docs/             # Tùy chọn: Tài liệu bổ sung
│   ├── advanced.md
│   └── troubleshooting.md
├── templates/        # Tùy chọn: Templates cho config/code
│   └── config.yaml
└── scripts/          # Tùy chọn: Script utility
    ├── validate.py
    └── parse.py
```

### 1.5 File SKILL.md

**Cấu trúc:**

```markdown
---
name: my-skill
description: Mô tả ngắn về skill này làm gì và khi nào sử dụng.
---

# My Skill

Hướng dẫn chi tiết cho Cline khi skill này được kích hoạt.

## Steps
1. Bước đầu tiên
2. Bước thứ hai
3. Tài liệu nâng cao: xem [advanced.md](docs/advanced.md)

## Important Rules
⚠️ **MUST** follow these rules...

## Examples
Ví dụ thực tế...
```

**Các trường bắt buộc:**
- `name`: Phải khớp chính xác với tên thư mục (kebab-case)
- `description`: Cho Agent biết khi nào sử dụng skill (max 1024 ký tự)

---

## 2. Rule vs Workflow vs Skill

### 2.1 So sánh cốt lõi

| Đặc điểm | **Rule** | **Workflow** | **Skill** |
|----------|----------|-------------|-----------|
| **Bản chất** | Bộ điều kiện if/then | Chuỗi các bước cố định | Bộ kiến thức + instructions |
| **Ví von** | Sách luật | Công thức nấu ăn | Đầu bếp biết nấu |
| **Thực thi bởi** | Python code | Con người hoặc bot | AI Agent (có suy luận) |
| **Tốc độ** | Rất nhanh (ms) | Phụ thuộc steps | Chậm (cần suy luận) |
| **Độ chính xác** | 100% (deterministic) | Phụ thuộc người follow | Cao nhưng có thể sai |
| **Suy luận** | ❌ Không | ❌ Không | ✅ Có |
| **Correlate** | ❌ Không | ❌ Không | ✅ Có |
| **Giải thích** | ❌ Không | ❌ Không | ✅ Có |

### 2.2 Rule - Bộ luật tự động

**Định nghĩa:**
- Tập hợp các điều kiện đã define sẵn
- Chạy bằng code (Python), không cần AI
- Format: `NẾU [điều kiện] THÌ [kết quả] → [hành động]`

**Cấu trúc thực tế (JSON):**
```json
{
  "node_01_running_check": {
    "type": "check",
    "keys": ["Running"],
    "threshold": 50,
    "operator": "DUT.Running - REF.Running > threshold",
    "on_true": {
      "problem": "Running time increased",
      "suggestion": "Suggest app team checking"
    }
  }
}
```

**Đọc là:** "Nếu Running time DUT cao hơn REF quá 50ms → flag là vấn đề → gợi ý App team kiểm tra."

**Làm được:**
- ✅ Check threshold (A > B ?)
- ✅ Flag pass/fail
- ✅ Route đến team
- ✅ Xử lý 1000 apps/giây
- ✅ Chạy 24/7 tự động

**Không làm được:**
- ❌ Giải thích tại sao A > B
- ❌ Xếp hạng mức độ nghiêm trọng theo context
- ❌ Phân biệt primary vs secondary cause
- ❌ Correlate nhiều metrics liên quan

**Thế mạnh unique:**
- **Tốc độ + Scale**: Khi có 500 test results cần screen mỗi sáng → chỉ Rule xử lý được trong vài giây

### 2.3 Workflow - Quy trình từng bước

**Định nghĩa:**
- Chuỗi các bước phải thực hiện theo thứ tự cố định
- Mỗi bước rõ ràng: làm gì, input gì, output gì

**Ví dụ thực tế:**
```markdown
# Workflow: Chạy performance test pipeline

1. Copy trace files từ device:
   ```
   adb pull /sdcard/traces/ D:\FE\Data\<model>\
   ```

2. Chạy extraction:
   ```
   python execution_sql.py --dut D:\FE\Data\DUT\ --ref D:\FE\Data\REF\
   ```

3. Kiểm tra Output:
   - Có DUT_*.json? → tiếp
   - Không có? → check log, chạy lại bước 2

4. Chạy Rule screening

5. Nếu có app FAIL → dùng Skill phân tích
```

**Làm được:**
- ✅ Đảm bảo thứ tự đúng
- ✅ Ai cũng follow được
- ✅ Không quên bước nào
- ✅ Tự động hóa được
- ✅ Training newbie

**Không làm được:**
- ❌ Quyết định khi gặp case lạ
- ❌ Phân tích data phức tạp
- ❌ Adapt khi input bất ngờ
- ❌ Giải thích tại sao

**Thế mạnh unique:**
- **Consistency + Onboarding**: Đảm bảo quy trình được thực hiện đúng thứ tự, không skip bước nào

### 2.4 Skill - Bộ kiến thức cho AI

**Định nghĩa:**
- Bộ tài liệu chuyên sâu (SKILL.md + references) giúp AI Agent hiểu context, kiến thức domain
- Agent đọc Skill → có đủ kiến thức → suy luận → trả lời

**Cấu trúc:**
```
app_launch_rca.skill/
├── SKILL.md                        ← Instructions chính
└── references/
    ├── json_schema.md              ← Cấu trúc data
    ├── workflow_rules.md           ← Logic diagnostic  
    ├── metric_glossary.md          ← Định nghĩa metrics
    └── team_routing.md             ← Issue → Team mapping
```

**Làm được:**
- ✅ Correlate nhiều metrics
- ✅ Giải thích "tại sao"
- ✅ Handle case chưa gặp
- ✅ Trả lời câu hỏi tự do
- ✅ Tạo report theo context
- ✅ So sánh phức tạp

**Không làm được:**
- ❌ Xử lý 1000 apps/giây (chậm)
- ❌ 100% chính xác (có thể suy luận sai)
- ❌ Deterministic (khác lần chạy khác output)
- ❌ Chạy offline không có AI

**Thế mạnh unique:**
- **Suy luận + Giải thích**: Khi PE hỏi "Tại sao gallery chậm hơn 337ms?" → chỉ Skill trả lời được

### 2.5 Khi nào dùng gì?

| Use Case | Dùng Rule | Dùng Workflow | Dùng Skill |
|----------|-----------|---------------|------------|
| Screen nhanh 100 apps | ✅ | ❌ | ❌ |
| Automated CI/CD gate | ✅ | ✅ | ❌ |
| Quy trình lặp hàng ngày | ❌ | ✅ | ❌ |
| Onboarding người mới | ❌ | ✅ | ❌ |
| Cần phân tích "tại sao" | ❌ | ❌ | ✅ |
| Correlate nhiều metrics | ❌ | ❌ | ✅ |
| Case chưa gặp trước | ❌ | ❌ | ✅ |
| Q&A interactive | ❌ | ❌ | ✅ |

---

## 3. Workflow vs Skill - Sự khác biệt

### 3.1 So sánh chi tiết

| Đặc điểm | **Workflow** | **Skill** |
|----------|--------------|-----------|
| **Bản chất** | Chuỗi các bước cố định | Bộ kiến thức + instructions |
| **Thực thi bởi** | Con người hoặc bot | AI Agent (có suy luận) |
| **Độ linh hoạt** | Rất thấp (cứng) | Cao (có thể adapt) |
| **Xử lý case lạ** | ❌ Không | ✅ Có |
| **Tốc độ** | Phụ thuộc steps | Chậm (cần suy luận) |
| **Deterministic** | 100% | 80-95% |
| **Suy luận** | ❌ Không | ✅ Có |
| **Scripts hỗ trợ** | ✅ Có (automation) | ✅ Có (nhưng mục đích khác) |

### 3.2 Tại sao Skill KHÔNG thay thế Workflow?

#### Lý do 1: Scripts trong Skill ≠ Scripts trong Workflow

| Scripts trong Skill | Scripts trong Workflow |
|---------------------|----------------------|
| **Mục đích**: Validation, computation, data processing | **Mục đích**: Automation step trong workflow |
| **Đặc điểm**: Deterministic, chỉ output vào context | **Đặc điểm**: Execute action, có side effects |
| **Ví dụ**: Validate config, parse file format | **Ví dụ**: Run extraction, pull files from device |
| **Dùng khi**: Cần tính toán tin cậy, tiết kiệm token | **Dùng khi**: Cần tự động hóa quy trình lặp lại |

#### Lý do 2: AI Agent không phải Orchestrator

```
Workflow = Director phim
- Quyết định: quay scene nào trước, scene nào sau
- Điều phối: diễn viên A, diễn viên B, máy quay
- Quyền lực: có thể dừng, quay lại, thay đổi kế hoạch
- Logic: if/else, loop, retry, abort

Skill = Chuyên gia tư vấn
- Được hỏi: "Làm sao để fix bug này?"
- Trả lời: "Theo kinh nghiệm, có 3 cách..."
- Quyền lực: KHÔNG quyết định, chỉ tư vấn
- Logic: suy luận, correlate, giải thích
```

**Skill có thể kèm script validate, nhưng Skill KHÔNG quyết định:**
- Khi nào chạy step nào
- Cần retry hay abort
- Điều kiện gì để move to next step

**Workflow thì khác:**

```python
# Workflow hardcode logic
if (trace files exist) {
    run_extraction()
    if (output valid) {
        continue()
    } else {
        retry(3) or abort()
    }
} else {
    send_alert()
    stop()
}
```

Workflow hardcode logic: if A then B. Agent không cần suy luận, chỉ execute.

#### Lý do 3: Agent không deterministic

**Ví dụ thực tế:**

```
Prompt: "Dùng skill running-workflow.md"

Lần 1:
Agent: "Check files → OK. Run extraction → ERROR. 
       Retry lần 1 → ERROR. Retry lần 2 → ERROR. 
       Retry lần 3 → ERROR. Thôi abort."

Lần 2 (cùng prompt):
Agent: "Check files → OK. Run extraction → ERROR. 
       Hmm, có thể do file permissions. 
       Để tôi check file permissions trước..."
       (Agent tự ý làm logic KHÔNG có trong skill)

Lần 3 (cùng prompt):
Agent: "Check files → OK. Run extraction → ERROR. 
       Hmm, để tôi thử extraction trước xem có được không..."
       (Agent NHẦM, chạy extraction dù trace files không tồn tại)
```

Workflow thì luôn giống nhau 100% mỗi lần chạy.

---

## 4. Script trong Skill

### 4.1 Ví von dễ hình dung

```
Agent (AI) = Chuyên gia tư vấn tài chính
- Có kiến thức sâu rộng về tài chính
- Có thể phân tích, đưa ra chiến lược
- NHƯNG cần công cụ để tính toán số liệu

Script trong Skill = Máy tính cầm tay
- Là công cụ hỗ trợ chuyên gia
- Chuyên gia nhập số liệu → máy tính tính kết quả
- Máy tính không đưa ra chiến lược, chỉ tính toán
- Chuyên gia dùng kết quả máy tính → đưa ra lời khuyên

Tương tự:
Agent → Chạy script → Nhận output → Suy luận → Đưa ra kết luận
(chuyên gia)   (máy tính)    (số liệu)   (phân tích)  (lời khuyên)
```

### 4.2 Script làm 4 việc chính

#### 1. Validate - Kiểm tra tính hợp lệ

**Mô tả:**
- Kiểm tra input có đúng format, cấu trúc không
- Kiểm tra các điều kiện cần thiết
- Nếu sai → báo lỗi, nếu đúng → cho tiếp tục

**Ví dụ: validate_input.py**

```python
import sys
import json
import os

def validate_json(file_path):
    """Validate JSON file structure"""
    
    # Check file exists
    if not os.path.exists(file_path):
        print("❌ File không tồn tại")
        return False
    
    # Check file size
    if os.path.getsize(file_path) == 0:
        print("❌ File rỗng")
        return False
    
    # Check JSON format
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON format sai: {e}")
        return False
    
    # Check required fields
    required_fields = ['apps_data', 'device_code', 'timestamp']
    for field in required_fields:
        if field not in data:
            print(f"❌ Thiếu field bắt buộc: {field}")
            return False
    
    print(f"✅ JSON file hợp lệ - {len(data['apps_data'])} apps")
    return True

if __name__ == "__main__":
    file_path = sys.argv[1]
    validate_json(file_path)
```

**Agent chạy với script:**

```
Agent: "Trước khi phân tích, validate input file..."
       Chạy validate_input.py DUT.json
       Output: ✅ JSON file hợp lệ - 2 apps
       Agent: "OK, file hợp lệ. Bây giờ tôi phân tích..."
```

---

#### 2. Parse - Phân tích/đọc dữ liệu phức tạp

**Mô tả:**
- Đọc file có format phức tạp (log, bugreport, custom format)
- Extract thông tin quan trọng
- Chuyển đổi format (raw text → JSON, CSV → structured data)

**Ví dụ: parse_bugreport.py**

```python
import sys
import re
import json

def parse_pss_section(content):
    """Parse 'Total PSS by process:' section"""
    pattern = r"Total PSS by process:(.*?)(?=\n\n|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return None
    
    section = match.group(1)
    lines = section.strip().split('\n')
    
    result = []
    for line in lines:
        if not line.strip():
            continue
        
        # Parse format: "314,911K: com.android.systemui (pid 2009)"
        match = re.match(r'([\d,]+)K:\s*(.+?)\s*\(pid\s+(\d+)\)', line)
        
        if match:
            size_kb = match.group(1).replace(',', '')
            process_name = match.group(2)
            pid = int(match.group(3))
            
            result.append({
                'process_name': process_name,
                'pid': pid,
                'pss_kb': int(size_kb),
                'pss_mb': int(size_kb) / 1024
            })
    
    return result

def main():
    bugreport_file = sys.argv[1]
    
    with open(bugreport_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    result = {
        'pss_by_process': parse_pss_section(content),
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

---

#### 3. Compute - Tính toán metrics phức tạp

**Mô tả:**
- Tính toán các metrics (mean, median, std dev, percentiles)
- Tính toán correlation, regression
- Tính toán performance metrics (FPS, latency, throughput)

**Ví dụ: calculate_stats.py**

```python
import sys
import json
import numpy as np

def calculate_statistics(values):
    """Calculate statistics for a list of values"""
    if not values:
        return None
    
    values = np.array(values)
    
    stats = {
        'count': len(values),
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'std_dev': float(np.std(values)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'p25': float(np.percentile(values, 25)),
        'p75': float(np.percentile(values, 75)),
        'p90': float(np.percentile(values, 90)),
        'p95': float(np.percentile(values, 95)),
        'p99': float(np.percentile(values, 99))
    }
    
    return stats

def main():
    json_file = sys.argv[1]
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract execution times (giả sử)
    execution_times = [555.357, 558.421, 552.893]
    
    stats = calculate_statistics(execution_times)
    
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

---

#### 4. Transform - Chuyển đổi format dữ liệu

**Mô tả:**
- Chuyển đổi từ format này sang format khác (CSV → JSON, XML → JSON)
- Reshape/restructure data (flatten nested JSON, aggregate data)
- Normalize data (chuẩn hóa format, loại bỏ duplicates)

**Ví dụ: transform_csv_to_json.py**

```python
import sys
import csv
import json

def csv_to_json(csv_file):
    """Convert CSV performance results to JSON"""
    
    apps = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            app_name = row['app']
            dut_time = float(row['execution_time'])
            ref_time = float(row['ref'])
            
            diff = dut_time - ref_time
            diff_percent = (diff / ref_time) * 100
            
            # Determine status
            if diff > 100 or diff_percent > 15:
                status = "FAIL"
            elif diff > 30 or diff_percent > 5:
                status = "WARNING"
            else:
                status = "PASS"
            
            app_data = {
                'name': app_name,
                'dut_execution_time_ms': dut_time,
                'ref_execution_time_ms': ref_time,
                'diff_ms': diff,
                'diff_percent': diff_percent,
                'status': status
            }
            
            apps.append(app_data)
    
    result = {
        'total_apps': len(apps),
        'pass': sum(1 for app in apps if app['status'] == 'PASS'),
        'fail': sum(1 for app in apps if app['status'] == 'FAIL'),
        'warning': sum(1 for app in apps if app['status'] == 'WARNING'),
        'apps': apps
    }
    
    return result

def main():
    csv_file = sys.argv[1]
    
    result = csv_to_json(csv_file)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

### 4.3 Lợi ích của Script trong Skill

✅ **Tiết kiệm Token**
- Script 500 dòng code → chỉ 50 tokens output load vào context
- Tiết kiệm ~1950 tokens mỗi lần chạy

✅ **Độ chính xác cao hơn**
- Code đã test, đã handle edge cases
- Regex đã validate, không dễ sai

✅ **Tốc độ nhanh hơn**
- Code đã optimize, dùng library (numpy, pandas)
- Vectorized operations → nhanh hơn code viết tay

✅ **Dễ bảo trì**
- Code ở một file, có version control
- Có unit test, dễ fix bug

### 4.4 Script KHÔNG nên làm gì

❌ **KHÔNG nên có side effects**

```python
# SAI
def validate_input(file_path):
    if not os.path.exists(file_path):
        send_alert_email(f"File not found: {file_path}")  # ❌ Không send email
        return False

# ĐÚNG
def validate_input(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File không tồn tại: {file_path}")  # ✅ Chỉ print
        return False
```

❌ **KHÔNG nên modify system**

```python
# SAI
def validate_input(file_path):
    if not os.path.exists(file_path):
        with open('error_log.txt', 'w') as f:  # ❌ Không write file
            f.write(f"File not found: {file_path}")
        return False
```

❌ **KHÔNG nên call API**

```python
# SAI
def check_api_status():
    response = requests.get('https://api.example.com/status')  # ❌ Không call API
    return response.json()
```

### 4.5 Tóm tắt: Script trong Skill

| Việc | Mô tả | Ví dụ |
|------|-------|-------|
| **Validate** | Kiểm tra input hợp lệ | validate_input.py - check JSON format |
| **Parse** | Đọc dữ liệu phức tạp | parse_bugreport.py - extract PSS |
| **Compute** | Tính toán metrics | calculate_stats.py - tính mean, std dev |
| **Transform** | Chuyển đổi format | transform_csv_to_json.py - CSV → JSON |

**Lợi ích:** Tiết kiệm token, chính xác, nhanh, dễ bảo trì

**Giới hạn:** KHÔNG side effects, KHÔNG modify system, CHỈ output

---

## 5. Important Rules trong Skill

### 5.1 Khái niệm

Important Rules là các guardrails (rào chắn) được define trong SKILL.md để **hướng dẫn Agent** tránh các lỗi phổ biến.

### 5.2 Ví dụ Important Rules

```markdown
## Important Rules

### Rule 1: Sequential Execution
⚠️ **MUST** follow steps in order:
1. Validate input
2. Run extraction
3. Check output
4. If output valid → analyze
5. If output invalid → retry max 3 times

❌ **NEVER** skip steps or reorder

### Rule 2: Stop Condition
⚠️ **MUST** stop immediately if:
- Trace files not found → Stop, do not attempt extraction
- Output validation fails 3 times → Abort workflow

### Rule 3: No Custom Logic
⚠️ **MUST NOT** add custom logic:
- ❌ Do NOT check alternative trace directories
- ❌ Do NOT attempt extraction if files not found
```

### 5.3 Important Rules giúp được gì?

✅ **Giảm Agent quên bước**
- Rules nhắc nhở Agent phải follow order
- Agent có thể nhớ "validate before extraction"

✅ **Giảm Agent tự ý thêm logic**
- Rules nói "DO NOT add custom logic"
- Agent có thể follow better

✅ **Giảm Agent nhầm logic**
- Rules define rõ "retry 3 times" = retry extraction
- Agent có thể hiểu đúng hơn

### 5.4 Important Rules KHÔNG giải quyết được gì?

❌ **Agent vẫn có thể VI PHẠM Rules**
- Rules = soft constraints, không phải hard constraints
- Agent có thể interpret rules khác
- Agent có thể override rules nếu nghĩ cần thiết

**Ví dụ thực tế:**

```
Lần 1:
Agent: "Check files → Not found. 
       Rule 2: 'MUST stop immediately'
       Stop workflow."
       ✅ Agent follow rule

Lần 2 (cùng skill, cùng input):
Agent: "Check files → Not found.
       Hmm, có thể files ở thư mục khác?
       Để tôi check D:\Traces\Backup\..."
       ❌ Agent VI PHẠM Rule 3 (No Custom Logic)
```

❌ **Agent vẫn KHÔNG deterministic**
- Cùng input, cùng rules → output có thể khác
- Agent có thể thêm debug step lần này, không lần khác

❌ **Rules KHÔNG thể enforce conditional branching**
- Rules define "if A then B" bằng ngôn ngữ tự nhiên
- Agent phải suy luận "A có đúng không?"
- Workflow hardcode "if A then B" bằng code → không suy luận

### 5.5 Tóm tắt: Important Rules

**Giúp được:** Giảm Agent quên, nhầm, tự ý logic (80-90% thời gian follow đúng)

**KHÔNG giải quyết được:**
- Agent vẫn có thể violate rules (10-20%)
- Agent không deterministic
- Rules không thể enforce conditional branching

**Kết luận:** Important Rules = Guardrails giúp Agent tốt hơn, nhưng KHÔNG thay thế Workflow

---

## 6. Kết hợp cả 3 trong thực tế

### 6.1 Pipeline thực tế

```
                    ┌─────────────┐
                    │  Trace Files │
                    └──────┬──────┘
                           ▼
              ┌────────────────────────┐
  WORKFLOW    │  1. Pull files          │
  (quy trình) │  2. Run extraction       │
              │  3. Check output exists  │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
  RULE        │  Screen 20 apps:        │
  (tự động)   │  ✅✅✅❌❌⚠️✅✅...     │
              │  → 2 FAIL, 1 WARNING    │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
  SKILL       │  Deep analysis:         │
  (AI phân    │  "gallery: D-state do   │
   tích)      │   Pageboost + parallel  │
              │   process"              │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
  SKILL       │  Generate report        │
  (AI tạo     │  → Markdown report      │
   report)    │  → Action items         │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
  WORKFLOW    │  4. Upload report       │
  (quy trình) │  5. Notify team         │
              └────────────────────────┘
```

### 6.2 Ai kiểm soát ai?

```
Workflow gọi → Rule (bước 4 trong workflow)
Workflow gọi → Skill (bước 5 trong workflow)
Skill chứa  → Rule (guardrails bên trong SKILL.md)
Rule feed   → Skill (Rule screen trước, Skill phân tích app fail)
```

### 6.3 Pipeline lý tưởng

```
Rule (100% chính xác, screen) 
    ↓
Skill (phân tích, có thể sai) 
    ↓
PE review (final)
```

Skill là **trợ lý**, không thay thế PE.

---

## 7. FAQ

### Q1: Nếu tôi define rất nhiều Rules, có thay thế được Skill không?

**Không hoàn toàn.**
- Define thêm Rules giúp cover nhiều cases hơn
- NHƯNG gặp 2 giới hạn:
  - **Combinatorial explosion**: 20 metrics → > 1 triệu tổ hợp
  - **Không xử lý unknown**: Process mới, pattern mới → phải thêm rule thủ công

Rule phù hợp cho **known patterns**. Skill phù hợp cho **unknown patterns + reasoning**.

---

### Q2: PE vẫn cần review output của Skill đúng không?

**Đúng.** Pipeline lý tưởng:
```
Rule (100% chính xác, screen) → Skill (phân tích, có thể sai) → PE review (final)
```

Skill là **trợ lý**, không thay thế PE.

---

### Q3: Agent tự chọn Skill hay tôi phải chỉ?

Agent có thể **tự chọn** dựa vào `name` + `description` trong frontmatter SKILL.md. Nhưng nếu prompt mơ hồ, chỉ đích danh sẽ chắc ăn hơn.

---

### Q4: Skill có cần update không?

**Có.** Khi gặp case mà Agent suy luận sai → thêm guardrail vào SKILL.md. Ví dụ:
- Agent sai về priority → thêm "Priority 110 = high" vào metric_glossary.md
- Agent miss correlation → thêm rule cụ thể vào workflow_rules.md

**SKILL.md là living document**, càng dùng càng tốt.

---

### Q5: Workflow có cần AI không?

Workflow **có thể** chạy hoàn toàn bằng người hoặc bot (không cần AI). Nhưng Workflow **có thể gọi Skill** ở 1 bước cụ thể (ví dụ: "Bước 5: Dùng Skill phân tích apps fail").

---

### Q6: Script trong Skill có thể thay thế Workflow được không?

**KHÔNG HOÀN TOÀN.** Script trong Skill:
- Là helper để Agent thông minh hơn
- KHÔNG quyết định flow
- KHÔNG có side effects
- Agent quyết định next step (có thể quên/nhầm)

Workflow:
- Orchestrate nhiều tools/scripts
- Hardcode conditional logic
- Có side effects (send email, write file)
- 100% deterministic

---

## 8. Kết luận

### 8.1 Tóm tắt nhanh

| Khái niệm | Là gì | Khi nào dùng |
|-----------|-------|--------------|
| **Rule** | Bộ điều kiện if/then (Python code) | Screen nhanh, automated CI/CD |
| **Workflow** | Chuỗi các bước cố định | Quy trình lặp, automation, onboarding |
| **Skill** | Bộ kiến thức + instructions cho AI | Phân tích "tại sao", correlate metrics, Q&A |

### 8.2 Script trong Skill

**Làm 4 việc:**
1. **Validate** - Kiểm tra input hợp lệ
2. **Parse** - Đọc dữ liệu phức tạp
3. **Compute** - Tính toán metrics
4. **Transform** - Chuyển đổi format

**Lợi ích:** Tiết kiệm token, chính xác, nhanh, dễ bảo trì

**Giới hạn:** KHÔNG side effects, KHÔNG modify system, CHỈ output

### 8.3 Important Rules

**Giúp được:** Giảm Agent quên, nhầm, tự ý logic (80-90% follow đúng)

**KHÔNG giải quyết được:** Agent vẫn có thể violate, không deterministic

### 8.4 Best Practices

1. **Kết hợp cả 3:** Workflow orchestrate → Rule screen → Skill analyze → PE review
2. **Script trong Skill:** Validate, parse, compute, transform - KHÔNG side effects
3. **Important Rules:** Giảm lỗi Agent, nhưng KHÔNG thay thế Workflow
4. **SKILL.md là living document:** Càng dùng càng tốt, update khi Agent sai

---

**Tài liệu tổng hợp hoàn thành!** 📚

Created: 2026-03-16  
Context: Tài liệu tham khảo cho việc làm việc với Skills, Workflow, Rule trong Cline AI Agent

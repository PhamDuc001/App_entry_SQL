# Rule vs Workflow vs Skill – Hướng dẫn cho Newbie

> Tài liệu này giải thích 3 khái niệm cốt lõi khi làm việc với AI Agent trong performance analysis.
> Tất cả ví dụ sử dụng data thực tế từ Android App Launch Performance testing.

---

## Mục lục

1. [Tổng quan nhanh](#1-tổng-quan-nhanh)
2. [Rule – Bộ luật tự động](#2-rule--bộ-luật-tự-động)
3. [Workflow – Quy trình từng bước](#3-workflow--quy-trình-từng-bước)
4. [Skill – Bộ kiến thức cho AI](#4-skill--bộ-kiến-thức-cho-ai)
5. [So sánh chi tiết](#5-so-sánh-chi-tiết)
6. [Khi nào dùng gì?](#6-khi-nào-dùng-gì)
7. [Kết hợp cả 3 trong thực tế](#7-kết-hợp-cả-3-trong-thực-tế)
8. [FAQ](#8-faq)

---

## 1. Tổng quan nhanh

| | **Rule** | **Workflow** | **Skill** |
|--|----------|-------------|-----------|
| **Là gì** | Bộ điều kiện if/then | Quy trình step-by-step | Bộ kiến thức + instructions cho AI |
| **Ví von** | Cuốn sách luật | Công thức nấu ăn | Đầu bếp biết nấu |
| **Ai chạy** | Code (Python) | Con người hoặc bot | AI Agent |
| **Tốc độ** | Rất nhanh (ms) | Phụ thuộc steps | Chậm (cần suy luận) |
| **Độ chính xác** | 100% (deterministic) | Phụ thuộc người follow | Cao nhưng có thể sai |

---

## 2. Rule – Bộ luật tự động

### 2.1 Khái niệm

Rule là **tập hợp các điều kiện đã define sẵn**, được chạy bằng **code** (không cần AI). Mỗi rule có 3 phần:

```
NẾU [điều kiện] THÌ [kết quả] → [hành động]
```

### 2.2 Cấu trúc thực tế

Trong project, Rule được lưu dưới dạng JSON:

```json
// File: AI_performance_root_workflow_v1_2.json

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

Đọc là: *"Nếu Running time DUT cao hơn REF quá 50ms → flag là vấn đề → gợi ý App team kiểm tra."*

### 2.3 Chức năng

| Làm được | Không làm được |
|----------|---------------|
| ✅ Check threshold (A > B ?) | ❌ Giải thích tại sao A > B |
| ✅ Flag pass/fail | ❌ Xếp hạng mức độ nghiêm trọng theo context |
| ✅ Route đến team | ❌ Phân biệt primary vs secondary cause |
| ✅ Xử lý 1000 apps/giây | ❌ Trả lời câu hỏi follow-up |
| ✅ Chạy 24/7 tự động | ❌ Correlate nhiều metrics liên quan |

### 2.4 Ví dụ – Rule screenning 20 apps

**Input**: JSON data 20 apps, mỗi app có Running, Sleeping, D-state, compiler...

**Rule chạy** (< 1 giây):
```
✅ camera:      Running +12ms [PASS], D-state +3ms [PASS]
✅ clock:       Running +8ms [PASS], D-state +1ms [PASS]
⚠️ calculator:  Running +28ms [PASS], Compiler verify ≠ REF [FLAG]
❌ gallery:     D-state +253ms [FAIL > 30ms] → Kernel Memory team
❌ message:     Running +597ms [FAIL > 50ms] → App team
... (15 more apps in 0.1 giây)
```

**Output**: Danh sách pass/fail/flag – **không giải thích**, chỉ kiểm tra.

### 2.5 Thế mạnh unique (chỉ Rule làm tốt)

**Tốc độ + Scale**: Khi có 500 test results cần screen mỗi sáng → chỉ Rule xử lý được trong vài giây. Workflow phải làm thủ công. Skill (AI) mất hàng giờ và tốn tiền.

---

## 3. Workflow – Quy trình từng bước

### 3.1 Khái niệm

Workflow là **chuỗi các bước** phải thực hiện **theo thứ tự** cố định. Mỗi bước có thể là: chạy command, mở file, check điều kiện, hoặc gọi tool khác.

### 3.2 Cấu trúc thực tế

Workflow thường được lưu dưới dạng Markdown:

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

6. Upload report lên shared drive
```

### 3.3 Chức năng

| Làm được | Không làm được |
|----------|---------------|
| ✅ Đảm bảo thứ tự đúng | ❌ Quyết định khi gặp case lạ |
| ✅ Ai cũng follow được | ❌ Phân tích data phức tạp |
| ✅ Không quên bước nào | ❌ Adapt khi input bất ngờ |
| ✅ Tự động hóa được | ❌ Giải thích tại sao |
| ✅ Training newbie | ❌ Suy luận, correlate |

### 3.4 Ví dụ – Workflow xử lý bugreport

```markdown
# Workflow: Extract bugreport data

1. Tìm file Bugreport*.zip trong trace folder
2. Đọc nội dung (giải nén hoặc in-memory)
3. Tìm section "Total PSS by process:"
4. Parse format: "314,911K: com.android.systemui (pid 2009)"
5. Lưu mapping {PID: process_name}
6. Match bugreport với trace files theo app group (1-6)
7. Extract metrics: uptime, compiler, PSS, pageboost
8. Ghi vào JSON output
```

Mỗi bước rõ ràng, **không cần phán đoán** → PE mới vào team cũng làm được.

### 3.5 Thế mạnh unique (chỉ Workflow làm tốt)

**Consistency + Onboarding**: Đảm bảo quy trình 8 bước được thực hiện đúng thứ tự, không skip bước nào. Rule không biết "thứ tự", Skill có thể quên bước.

---

## 4. Skill – Bộ kiến thức cho AI

### 4.1 Khái niệm

Skill là **bộ tài liệu chuyên sâu** (SKILL.md + references) giúp AI Agent hiểu **context, kiến thức domain, và hướng dẫn phân tích**. Agent đọc Skill → có đủ kiến thức để phân tích, suy luận, và trả lời câu hỏi.

### 4.2 Cấu trúc thực tế

```
app_launch_rca.skill/
├── SKILL.md                        ← Instructions chính
└── references/
    ├── json_schema.md              ← Cấu trúc data
    ├── workflow_rules.md           ← Logic diagnostic  
    ├── metric_glossary.md          ← Định nghĩa metrics
    └── team_routing.md             ← Issue → Team mapping
```

SKILL.md có 2 phần quan trọng:

**Phần 1 – Guardrails (Rules embed trong Skill):**
```markdown
## Check 2.1a – Compiler:
- Rule: Nếu DUT.compiler == "verify" VÀ DUT.compiler ≠ REF.compiler
  → Đây là guardrail: chỉ flag compiler khi DUT KHÁC REF
  → Nếu cả hai đều "verify" → không phải nguyên nhân cho diff
```

**Phần 2 – Free reasoning (phần AI tự suy luận):**
```markdown
## Step 5: Report Generation
→ Agent tự tổng hợp findings, correlate, và sinh report
→ Không define trước format cứng cho mọi trường hợp
```

### 4.3 Chức năng

| Làm được | Không làm được |
|----------|---------------|
| ✅ Correlate nhiều metrics | ❌ Xử lý 1000 apps/giây (chậm) |
| ✅ Giải thích "tại sao" | ❌ 100% chính xác (có thể suy luận sai) |
| ✅ Handle case chưa gặp | ❌ Deterministic (khác lần chạy khác output) |
| ✅ Trả lời câu hỏi tự do | ❌ Chạy offline không có AI |
| ✅ Tạo report theo context | ❌ Thay thế PE review (vẫn cần người duyệt) |

### 4.4 Ví dụ – Skill phân tích gallery

**Input**: DUT gallery data (D-state +253ms, Pageboost giảm, parallel process)

**Skill output**:
```markdown
## Gallery Analysis – D-state +253ms

### Root Cause Hypothesis

1. D-state spike +253ms rất lớn + Pageboostd chỉ 23.95 MB (REF: 30.23 MB)
   → Pageboost prefetch giảm → app phải đọc thêm từ disk
   → PRIMARY CAUSE

2. start_process_abnormal ở cycle 2: .android.scloud, com.samsung.cmh
   → 2 process khởi động song song, tranh chấp I/O
   → SECONDARY CAUSE
   
3. Cycle 1: systemui +364ms → nhưng cycle 2-3 ổn định
   → One-time warmup, NOT systematic issue

### Actions (prioritized)
| Priority | Team           | Action                          |
|----------|----------------|---------------------------------|
| High     | Kernel Memory  | Pageboost giảm 6.28MB → check   |
| Medium   | SWPL           | .android.scloud parallel → fix  |
| Low      | -              | Cycle 1 warmup → monitor only   |
```

**Chú ý**: Agent **correlate** D-state với Pageboost, **phân biệt** primary/secondary cause, **nhận diện** cycle 1 là outlier – điều Rule và Workflow không làm được.

### 4.5 Thế mạnh unique (chỉ Skill làm tốt)

**Suy luận + Giải thích**: Khi PE hỏi "Tại sao gallery chậm hơn 337ms?" → chỉ Skill trả lời được vì cần correlate nhiều metrics, phân biệt nguyên nhân chính/phụ, và xử lý case chưa từng gặp.

### 4.6 Giới hạn quan trọng

Skill = **Rule (guardrails)** + **AI reasoning (suy luận)**

```
SKILL.md define sẵn (guardrails):        AI tự suy luận:
────────────────────────────────         ──────────────────────
• Thresholds (> 50ms, > 30ms)           • Correlate metrics
• "Priority 110 = high, 120 = low"      • Identify outlier cycle
• "Compiler: chỉ flag khi DUT ≠ REF"    • Rank primary/secondary
• "NEVER fabricate data"                 • Handle new process names
• Team routing table                     • Answer follow-up Q&A
```

**Nếu guardrails thiếu**, Agent có thể suy luận sai. Ví dụ:
- Không define "Priority 110 = high" → Agent nghĩ 120 > 110 = better
- Không define "compiler chỉ flag khi khác nhau" → Agent flag cả khi cả hai đều verify

**→ SKILL.md càng chi tiết domain knowledge → AI càng ít sai.**

---

## 5. So sánh chi tiết

### 5.1 Ai thực thi?

```
Rule:     Python code → chạy trên máy → không cần internet
Workflow: Con người follow steps → hoặc bot chạy sequential
Skill:    AI Agent đọc instructions → suy luận → output
```

### 5.2 Tính deterministic

| Input giống nhau → Output? | Rule | Workflow | Skill |
|----------------------------|------|----------|-------|
| Lần 1 | ❌ FAIL | Bước 1→2→3→Done | "D-state do Pageboost, priority High" |
| Lần 2 | ❌ FAIL | Bước 1→2→3→Done | "D-state do Pageboost + memory, priority High" |
| Lần 3 | ❌ FAIL | Bước 1→2→3→Done | "Primary: Pageboost, Secondary: parallel process" |

Rule: **luôn giống nhau**. Skill: nội dung đúng nhưng **cách trình bày có thể khác**.

### 5.3 Xử lý case mới

**Case**: Lần đầu gặp process `com.samsung.cmh` khởi động parallel

| | Response |
|--|---------|
| **Rule** | ✅ Flag "start_process_abnormal exists" → nhưng không biết `com.samsung.cmh` là gì |
| **Workflow** | "Bước 4: Check abnormal processes" → thấy có → nhưng bước tiếp theo là gì? Workflow không define |
| **Skill** | "com.samsung.cmh khởi động song song ở cycle 2, correlate với CPU spike → SWPL investigate" |

### 5.4 Scalability

| Xử lý bao nhiêu apps | Rule | Workflow | Skill |
|----------------------|------|----------|-------|
| 1 app | 🐇 0.01s | 🐢 15 min (manual) | 🐕 30s |
| 20 apps | 🐇 0.1s | 🐢 5h (manual) | 🐕 10 min |
| 500 apps | 🐇 0.5s | ❌ Không khả thi | ❌ Quá chậm + tốn token |

---

## 6. Khi nào dùng gì?

### Dùng Rule khi:

| Scenario | Ví dụ |
|----------|-------|
| Screen nhanh nhiều data | "20 apps, app nào fail?" |
| Automated CI/CD gate | "Block build nếu Running > 100ms" |
| Alert/notification | "Email khi D-state > 30ms" |
| Logic đã biết, không cần suy luận | "Uptime > 10 → invalid" |
| Cần 100% deterministic | Compliance check |

### Dùng Workflow khi:

| Scenario | Ví dụ |
|----------|-------|
| Quy trình lặp hàng ngày | "Mỗi sáng: pull trace → run tool → check" |
| Onboarding người mới | "Follow 8 bước này để chạy test" |
| Automation pipeline | Bot chạy sequential steps |
| Nhiều steps phụ thuộc thứ tự | "Extract → Parse → Match → Output" |
| Cần reproducible | "Mọi người làm cùng 1 cách" |

### Dùng Skill khi:

| Scenario | Ví dụ |
|----------|-------|
| Cần phân tích "tại sao" | "Tại sao gallery chậm 337ms?" |
| Correlate nhiều metrics | "Running ↑ liên quan gì đến frequency?" |
| Case chưa gặp trước | "Process lạ xuất hiện, ảnh hưởng gì?" |
| Q&A interactive | "Cycle nào xấu nhất?" |
| Tạo report tùy context | "Report cho leadership vs cho App team" |
| So sánh phức tạp | "4GB vs 6GB vs 8GB – pattern gì?" |

---

## 7. Kết hợp cả 3 trong thực tế

### Pipeline thực tế:

```
                    ┌─────────────┐
                    │  Trace Files │
                    └──────┬──────┘
                           ▼
              ┌────────────────────────┐
  WORKFLOW    │  1. Pull files          │
  (quy trình) │  2. Run execution_sql   │
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

### Ai kiểm soát ai?

```
Workflow gọi → Rule (bước 4 trong workflow)
Workflow gọi → Skill (bước 5 trong workflow)
Skill chứa  → Rule (guardrails bên trong SKILL.md)
Rule feed   → Skill (Rule screen trước, Skill phân tích app fail)
```

---

## 8. FAQ

### Q: Nếu tôi define rất nhiều Rules, có thay thế được Skill không?

**Không hoàn toàn**. Define thêm Rules giúp cover nhiều cases hơn, nhưng gặp 2 giới hạn:
- **Combinatorial explosion**: 20 metrics → > 1 triệu tổ hợp điều kiện
- **Không xử lý unknown**: Process mới, pattern mới → phải thêm rule thủ công

Rule phù hợp cho **known patterns**. Skill phù hợp cho **unknown patterns + reasoning**.

### Q: PE vẫn cần review output của Skill đúng không?

**Đúng**. Pipeline lý tưởng:
```
Rule (100% chính xác, screen) → Skill (phân tích, có thể sai) → PE review (final)
```

Skill là **trợ lý**, không thay thế PE.

### Q: Agent tự chọn Skill hay tôi phải chỉ?

Agent có thể **tự chọn** dựa vào `name` + `description` trong frontmatter SKILL.md. Nhưng nếu prompt mơ hồ, chỉ đích danh sẽ chắc ăn hơn.

### Q: Skill có cần update không?

Có. Khi gặp case mà Agent suy luận sai → thêm guardrail vào SKILL.md. Ví dụ:
- Agent sai về priority → thêm "Priority 110 = high" vào metric_glossary.md
- Agent miss correlation → thêm rule cụ thể vào workflow_rules.md

**SKILL.md là living document**, càng dùng càng tốt.

### Q: Workflow có cần AI không?

Workflow **có thể** chạy hoàn toàn bằng người hoặc bot (không cần AI). Nhưng Workflow **có thể gọi Skill** ở 1 bước cụ thể (ví dụ: "Bước 5: Dùng Skill phân tích apps fail").

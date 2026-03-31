# PLM Test Analysis Workflow

## Overview

Workflow tự động hóa toàn bộ quy trình phân tích performance test từ PLM:
1. Download test logs từ PLM issue
2. Giải nén và organize files theo đúng cấu trúc thư mục
3. Chạy main_qt.py với các app fail
4. Phân tích output bằng skill app_launch_rca

## Workflow Steps

### Step 1: Download Test Logs từ PLM

**Input**: PLM ID (ví dụ: P260317-09524 hoặc P260130-07491)

**Actions**:
1. Sử dụng MCP PLM tool `get_defect_info` để lấy thông tin issue
2. Trích xuất thông tin từ `plmTitle` - Hỗ trợ cả 2 ngôn ngữ:

   **Tiếng Hàn (Korean) Pattern:**
   - Format: `[App성능][무부하실행시간/전체시간][{Model}][{RAMSize}][{DUT_Binary}] {Model} {DeviceCode} 무부하실행시간 시험 {Model} {DeviceCode} 대비 열세 件`
   - Ví dụ: `[App성능][무부하실행시간/전체시간][A266B][8GB][ZC5] A266B BOS 무부하실행시간 시험 A266B BOS 대비 열세 件`
   - Result: Model=A266B, RAM=8GB, DUT_Binary=ZC5, DeviceCode=BOS

   **Tiếng Anh (English) Pattern:**
   - Format: `[SW Perf&Field P]No load basic app entry speed/Execution time][{Model}_{Region}][{RAMSize}]{Model} {DUT_Binary} {DeviceCode} FAIL vs {Model} {REF_Binary} {DeviceCode}`
   - Ví dụ: `[SW Perf&Field P]No load basic app entry speed/Execution time][X306B_EUR][6GB]X306B ZC4 BOS FAIL vs X306B YK1 BOS`
   - Result: Model=X306B, RAM=6GB, DUT_Binary=ZC4, REF_Binary=YK1, DeviceCode=BOS

3. Trích xuất REF binary từ **header bảng test results trong content**:
   - Đọc trường `content` từ PLM issue
   - Tìm header của bảng test results
   - Phân tích cấu trúc header để lấy REF binary:
   
   **Tiếng Hàn (Korean) Header Structure:**
   ```
   항 목
   최초 실행
   A266B (ZC5_8GB)  ← DUT
   A266B (YH3_8GB)  ← REF (extract this)
   비교기준 (0.1초)
   ```
   - Pattern: `{Model} \({REF_Binary}_{RAMSize}\)`
   - Ví dụ: `A266B (YH3_8GB)` → REF_Binary=YH3, RAMSize=8GB

   **Tiếng Anh (English) Header Structure:**
   ```
   App Name
   Initial Entry
   X306B 6GB_ZC4  ← DUT
   X306B 6GB_YK1  ← REF (extract this)
   Test Std. (0.1sec)
   ```
   - Pattern: `{Model} {RAMSize}_{REF_Binary}`
   - Ví dụ: `X306B 6GB_YK1` → REF_Binary=YK1, RAMSize=6GB

4. Sử dụng MCP PLM tool `get_file_list` để lấy danh sách attachments

5. Xác định file log mới nhất:
   - Pattern: `{Model}{Binary}_{DeviceCode}_{RAMSize}_{Date}_LOG.zip`
   - Ví dụ: `A266BZC5_BOS_8GB_85_260327_LOG.zip`
   - Lấy file có DUT_Binary mới nhất (theo timestamp trong tên file hoặc createDate)
   - File REF: Tìm file có REF binary trong danh sách attachments

6. Sử dụng MCP PLM tool `get_file_url` để lấy download link cho cả DUT và REF

7. Tạo thư mục đích:
   - **Cấu trúc**: `D:\Log PLM\VOC\test\{Model}\{RAMSize}_{PLM_ID}\{BinaryVersion}\`
   - **Ví dụ**: `D:\Log PLM\VOC\test\A266B\8GB_P260317-09524\ZC5\`
   - Tự động tạo cấu trúc thư mục nếu chưa tồn tại

8. Download cả DUT và REF files .zip vào cùng thư mục đích:
   - DUT file: `{Model}{DUT_Binary}_{DeviceCode}_{RAMSize}_{Date}_LOG.zip`
   - REF file: `{Model}{REF_Binary}_{DeviceCode}_{RAMSize}_{Date}_LOG.zip`

**Output**: Cả 2 files .zip (DUT + REF) đã được download vào thư mục đúng

---

### Step 2: Giải nén Test Logs

**Input**: Đường dẫn đến thư mục chứa cả DUT và REF .zip files

**Actions**:
1. Chạy script giải nén cho DUT file:
   ```powershell
   python .clinerules/workflows/scripts/extract_test_logs.py --zip-path "<path_to_DUT_zip>" --output-dir "<test_folder>"
   ```
2. Chạy script giải nén cho REF file:
   ```powershell
   python .clinerules/workflows/scripts/extract_test_logs.py --zip-path "<path_to_REF_zip>" --output-dir "<test_folder>"
   ```
3. Script sẽ giải nén vào cùng thư mục đích
4. Kiểm tra các file quan trọng đã được giải nén:
   - Main log files từ cả DUT và REF
   - Output folder (nếu có sẵn từ các lần test trước)
   - Các file cấu hình

**Output**: Cả 2 files đã được giải nén vào cùng thư mục, sẵn sàng để chạy test

---

### Step 3: Xác định Fail Apps

**Input**: PLM ID, thông tin từ `get_defect_info`

**Actions**:
1. Đọc trường `content` từ PLM issue
2. Phân tích bảng test results trong content - Hỗ trợ cả 2 ngôn ngữ:

   **Cấu trúc bảng:**
   - Format: Table với các cột: App Name, DUT Version, REF Version, DUT Time, REF Time, Diff, Result
   - Header có thể tiếng Hàn hoặc tiếng Anh

   **Tiếng Hàn (Korean) - Ví dụ P260317-09524:**
   - Keywords fail: "열세" (yếu kém), "FAIL"
   - Ví dụ: Gallery (Albums) với kết quả +0.11s "열세"

   **Tiếng Anh (English) - Ví dụ P260130-07491:**
   - Keywords fail: "inferior", "FAIL"
   - Ví dụ: Gallery (Albums) với kết quả +0.11s "inferior", Message với +0.14s "inferior"

3. Trích xuất danh sách fail apps:
   - Phân tích ngôn ngữ từ content (tiếng Hàn hoặc tiếng Anh)
   - Dùng regex pattern phù hợp:
     - Tiếng Hàn: Tìm dòng có "열세" hoặc "FAIL" trong cột Result
     - Tiếng Anh: Tìm dòng có "inferior" hoặc "FAIL" trong cột Result
   - Lấy tên app từ cột "App Name"
   - Lưu thông tin: App Name, Diff (speed degradation)

4. Báo cáo cho user:
   - Danh sách apps fail
   - Speed degradation cho từng app
   - Số lượng apps cần test lại

**Ví dụ P260317-09524 (Tiếng Hàn):**
```
Fail Apps:
1. Gallery (Albums) - +0.11s degradation
```

**Ví dụ P260130-07491 (Tiếng Anh):**
```
Fail Apps:
1. Gallery (Albums) - +0.11s degradation
2. Message - +0.14s degradation
3. Samsung Notes - +0.20s degradation
4. Setting - +0.11s degradation
5. Recent - +0.11s degradation
```

**Output**: Danh sách apps fail để chạy test với main_qt.py

---

### Step 4: Chạy Test với main_qt.py

**Input**: Danh sách apps fail, đường dẫn đến thư mục test

**Actions**:
1. Gửi cho user danh sách apps fail và lệnh chạy:
   ```
   python main_qt.py --apps "<app1,app2,app3>" --path "<test_folder_path>"
   ```
2. User chạy lệnh, GUI hiện ra
3. User thực hiện test
4. main_qt.py tạo folder `Output/` với:
   - `DUT_{Model}_{Version}_{Timestamp}.json`
   - `REF_{Model}_{Version}_{Timestamp}.json`

**Output**: Folder Output với 2 file JSON

---

### Step 5: Phân tích Performance với app_launch_rca Skill

**Input**: Đường dẫn đến Output folder

**Actions**:
1. Load skill `app_launch_rca`
2. Đọc knowledge base (INDEX.md + các articles liên quan)
3. Đọc DUT và REF JSON files
4. Chạy 3-flow diagnostic analysis:
   - Flow 1: Initial Validation
   - Flow 2: Core Performance State Analysis
   - Flow 3: Resource Usage & Process Analysis
5. Tạo performance report chi tiết

**Output**: Báo cáo phân tích với:
- Executive summary
- Detailed findings per app
- Root cause analysis
- Team routing
- Action items

---

## Script References

### extract_test_logs.py
Location: `.clinerules/workflows/scripts/extract_test_logs.py`

Usage:
```powershell
python .clinerules/workflows/scripts/extract_test_logs.py --zip-path "<path_to_zip>" [--output-dir "<output_directory>"]
```

Features:
- Giải nén file .zip
- Xử lý encoding UTF-8
- Tạo cấu trúc thư mục nếu cần
- Log tiến trình giải nén
- Xử lý lỗi và báo cáo

---

## Example Usage

### Cách gọi Workflow

```
Agent, hãy chạy workflow PLM test analysis với PLM ID P260317-09524
```

### Agent sẽ thực hiện:

1. **Kết nối PLM**:
   - Đọc issue P260317-09524
   - Lấy thông tin Model: A266B, RAM: 8GB
   - Lấy thông tin Binary: ZC5 (DUT), YH3 (REF)

2. **Download**:
   - Tìm file log mới nhất trong attachments
   - Tạo thư mục: `D:\Log PLM\VOC\test\A266B\8GB_P260317-09524\ZC5\`
   - Download file zip vào thư mục

3. **Giải nén**:
   - Chạy `extract_test_logs.py`
   - Giải nén file zip

4. **Xác định Fail Apps**:
   - Đọc từ PLM: gallery, calculator, camera
   - Báo cáo cho user

5. **Chạy Test**:
   - Gửi lệnh:
     ```
     python main_qt.py --apps "gallery,calculator,camera" --path "D:\Log PLM\VOC\test\A266B\8GB_P260317-09524\ZC5\"
     ```
   - User chạy test

6. **Phân tích**:
   - Đọc Output folder
   - Chạy app_launch_rca skill
   - Tạo báo cáo chi tiết

---

## MCP PLM Tools Usage

### get_defect_info
Lấy thông tin chi tiết về PLM issue:
```python
plm.get_defect_info(
    defect="P260317-09524",
    division=""  # Optional
)
```

### get_file_list
Lấy danh sách file đính kèm:
```python
plm.get_file_list(
    defect="P260317-09524",
    division="",
    module="OP_DEFECT_ATTACH"  # Attachments
)
```

### get_file_url
Lấy URL để download file:
```python
plm.get_file_url(
    doc="DOC_ID",
    title="File Title",
    file="FILE_ID",
    division=""
)
```

---

## Troubleshooting

### Issue: Không thể download file từ PLM
- Kiểm tra MCP PLM server đã được enable
- Kiểm tra authentication token
- Kiểm tra quyền truy cập vào issue

### Issue: Giải nén thất bại
- Kiểm tra file .zip không bị corrupt
- Kiểm tra dung lượng đĩa đủ
- Kiểm tra quyền ghi vào thư mục đích

### Issue: main_qt.py không chạy được
- Kiểm tra Python environment
- Kiểm tra dependencies đã được cài đặt
- Kiểm tra đường dẫn đến thư mục test đúng

---

## Dependencies

- Python 3.x
- MCP PLM server (đã được enable)
- main_qt.py (đã có sẵn)
- app_launch_rca skill (đã có sẵn)
- zipfile module (built-in)

---

## Notes

- Workflow này được thiết kế để tối ưu hóa quy trình phân tích performance test
- Tự động hóa các bước thủ công lặp lại
- Giảm thiểu lỗi do thao tác thủ công
- Đảm bảo cấu trúc thư mục nhất quán
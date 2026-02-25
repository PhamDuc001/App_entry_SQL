# abnormal_memory.py - Improvements for pageboost_main.py Integration

## Overview
File `abnormal_memory.py` đã được cải tiến để hỗ trợ tích hợp với `pageboost_main.py`, cho phép tái sử dụng các file dumpstate đã được giải nén trong folder `_tmp`.

## Key Improvements

### 1. Auto-Detection Logic
- **Function**: `analyze_folder()` now accepts `extracted: bool = None`
- **Behavior**: Tự động phát hiện nguồn dữ liệu:
  - Ưu tiên 1: Nếu có folder `_tmp` với file `.txt` → dùng file đã giải nén
  - Ưu tiên 2: Nếu có file `.zip` → giải nén và xử lý
  - Ưu tiên 3: Nếu có thư mục đã giải nén → xử lý từ thư mục

### 2. New Function: `collect_all_data_from_tmp_folder()`
```python
def collect_all_data_from_tmp_folder(self, folder: Path) -> Tuple[List[UptimeData], List[CrashData]]:
```
- **Purpose**: Xử lý file dumpstate trong folder `_tmp` được tạo bởi `pageboost_main.py`
- **Logic**: Map file `.txt` với part name dựa trên thứ tự file ZIP gốc

### 3. Smart File-to-Part Mapping
- **Input**: File ZIP gốc (ví dụ: `A155FZA1_BOS_4GB_260108_S1_260108_195013_1part_Bugreport.zip`)
- **Process**: 
  1. Lấy danh sách file ZIP gốc và sắp xếp
  2. Lấy danh sách file `.txt` trong `_tmp` và sắp xếp theo timestamp
  3. Map file `.txt` với part name dựa trên thứ tự tương ứng
- **Output**: Part name chính xác (1part, 2part, etc.)

### 4. Updated Main Function
```python
if __name__ == "__main__":
    if len(sys.argv) == 3:
        folder1 = sys.argv[1]
        folder2 = sys.argv[2]
        config = Config()
        dut = DUT(folder1, config)
        ref = REF(folder2, config)
        # Sử dụng auto-detection (extracted=None)
        analyze_device_performance(dut, ref)
```

## Usage Scenarios

### Scenario 1: Using pageboost_main.py Output
1. Run `pageboost_main.py` → tạo folder `_tmp` với file `.txt`
2. Run `abnormal_memory.py` → tự động phát hiện và dùng file trong `_tmp`

### Scenario 2: Traditional ZIP Files
- Không có folder `_tmp`
- Code sẽ giải nén file ZIP như cũ

### Scenario 3: Extracted Folders
- Có các thư mục `*Bugreport`
- Code sẽ xử lý từ thư mục đã giải nén

## Benefits

1. **Performance**: Tái sử dụng file đã giải nén, không cần giải nén lại
2. **Integration**: Hoạt động tốt với workflow `pageboost_main.py`
3. **Backward Compatibility**: Vẫn hỗ trợ các định dạng cũ
4. **Smart Detection**: Tự động chọn nguồn dữ liệu phù hợp

## File Structure Requirements

### For pageboost_main.py Integration:
```
DUT_folder/
├── _tmp/
│   ├── dumpstate-2026-08-05-21-10.txt  # (from 1part)
│   ├── dumpstate-2026-01-08-05-32-53.txt  # (from 2part)
│   └── ...
├── A155FZA1_BOS_4GB_260108_S1_260108_195013_1part_Bugreport.zip
├── A155FZA1_BOS_4GB_260108_S1_260108_200156_2part_Bugreport.zip
└── ...
```

### Traditional ZIP Structure:
```
DUT_folder/
├── A155FZA1_BOS_4GB_260108_S1_260108_195013_1part_Bugreport.zip
├── A155FZA1_BOS_4GB_260108_S1_260108_200156_2part_Bugreport.zip
└── ...
```

## Error Handling
- Graceful fallback khi không tìm thấy file
- Bỏ qua các file không thể truy cập
- Giữ lại logic cũ khi có lỗi

## Testing
- Syntax check: ✅ `python -m py_compile abnormal_memory.py`
- Backward compatibility: ✅ Vẫn hỗ trợ các định dạng cũ
- Integration ready: ✅ Sẵn sàng làm việc với `pageboost_main.py`

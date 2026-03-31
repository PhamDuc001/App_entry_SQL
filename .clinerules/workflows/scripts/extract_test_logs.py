#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract Test Logs Script

Giải nén file .zip chứa test logs từ PLM vào thư mục đích.
Xử lý encoding UTF-8 và tạo cấu trúc thư mục nếu cần.
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime


def print_progress(message):
    """In thông báo tiến trình với timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def validate_zip_file(zip_path):
    """
    Kiểm tra xem file zip có hợp lệ không
    
    Args:
        zip_path: Đường dẫn đến file zip
        
    Returns:
        bool: True nếu file hợp lệ, False nếu không
    """
    if not os.path.exists(zip_path):
        print_progress(f"❌ Lỗi: File không tồn tại: {zip_path}")
        return False
    
    if not zipfile.is_zipfile(zip_path):
        print_progress(f"❌ Lỗi: File không phải là định dạng zip hợp lệ: {zip_path}")
        return False
    
    return True


def extract_zip(zip_path, output_dir=None):
    """
    Giải nén file zip vào thư mục đích
    
    Args:
        zip_path: Đường dẫn đến file zip
        output_dir: Thư mục đích (mặc định là cùng thư mục với file zip)
        
    Returns:
        str: Đường dẫn đến thư mục đã giải nén
    """
    try:
        # Xác định thư mục đích
        if output_dir is None:
            output_dir = os.path.dirname(zip_path)
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        print_progress(f"📦 Bắt đầu giải nén: {zip_path}")
        print_progress(f"📂 Thư mục đích: {output_dir}")
        
        # Mở file zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Liệt kê nội dung
            file_list = zip_ref.namelist()
            total_files = len(file_list)
            print_progress(f"📋 Tổng số files trong zip: {total_files}")
            
            # Giải nén từng file
            extracted_files = []
            for i, file_info in enumerate(zip_ref.infolist(), 1):
                try:
                    # Xử lý tên file có encoding issue
                    filename = file_info.filename
                    
                    # Giải nén file
                    zip_ref.extract(file_info, output_dir)
                    extracted_files.append(filename)
                    
                    # In progress mỗi 50 files
                    if i % 50 == 0 or i == total_files:
                        print_progress(f"   Tiến độ: {i}/{total_files} files")
                    
                except UnicodeEncodeError as e:
                    print_progress(f"⚠️  Cảnh báo: Encoding error với file: {file_info.filename}")
                    continue
                except Exception as e:
                    print_progress(f"⚠️  Cảnh báo: Không thể giải nén {file_info.filename}: {e}")
                    continue
            
            print_progress(f"✅ Đã giải nén {len(extracted_files)}/{total_files} files")
        
        # Kiểm tra các folder quan trọng
        check_output_folder(output_dir)
        check_log_files(output_dir)
        
        return output_dir
        
    except zipfile.BadZipFile as e:
        print_progress(f"❌ Lỗi: File zip bị hỏng hoặc không hợp lệ: {e}")
        return None
    except PermissionError as e:
        print_progress(f"❌ Lỗi: Không có quyền truy cập thư mục: {e}")
        return None
    except Exception as e:
        print_progress(f"❌ Lỗi không xác định khi giải nén: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_output_folder(base_dir):
    """
    Kiểm tra xem có folder Output không
    
    Args:
        base_dir: Thư mục cơ sở để kiểm tra
    """
    output_path = os.path.join(base_dir, "Output")
    
    if os.path.exists(output_path):
        print_progress(f"📁 Tìm thấy thư mục Output: {output_path}")
        
        # Liệt kê files trong Output
        files = os.listdir(output_path)
        if files:
            print_progress(f"   - Files trong Output: {', '.join(files[:10])}")
            if len(files) > 10:
                print_progress(f"   - ... và {len(files) - 10} files khác")
    else:
        print_progress(f"ℹ️  Không tìm thấy thư mục Output (có thể chưa chạy test)")


def check_log_files(base_dir):
    """
    Kiểm tra các file log quan trọng
    
    Args:
        base_dir: Thư mục cơ sở để kiểm tra
    """
    important_files = [
        "test_log.txt",
        "performance.log",
        "main.log",
        "execution.log"
    ]
    
    found_logs = []
    for log_file in important_files:
        log_path = os.path.join(base_dir, log_file)
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            found_logs.append(f"{log_file} ({size} bytes)")
    
    if found_logs:
        print_progress(f"📄 Tìm thấy log files:")
        for log in found_logs:
            print_progress(f"   - {log}")
    else:
        print_progress(f"ℹ️  Không tìm thấy log files trong thư mục")


def print_summary(zip_path, output_dir):
    """
    In tóm tắt sau khi giải nén
    
    Args:
        zip_path: Đường dẫn file zip
        output_dir: Thư mục đã giải nén
    """
    print_progress("\n" + "="*60)
    print_progress("TÓM TẮT GIẢI NÉN")
    print_progress("="*60)
    print_progress(f"File nguồn: {zip_path}")
    print_progress(f"Thư mục đích: {output_dir}")
    
    if output_dir and os.path.exists(output_dir):
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(output_dir)
            for filename in filenames
        )
        total_files = sum(
            len(filenames)
            for dirpath, dirnames, filenames in os.walk(output_dir)
        )
        print_progress(f"Tổng số files: {total_files}")
        print_progress(f"Tổng dung lượng: {total_size / (1024*1024):.2f} MB")
        print_progress(f"✅ Giải nén hoàn tất!")
    else:
        print_progress(f"❌ Giải nén thất bại!")
    
    print_progress("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Giải nén file test logs từ PLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python extract_test_logs.py --zip-path "D:\\Log PLM\\test.zip"
  python extract_test_logs.py --zip-path "D:\\Log PLM\\test.zip" --output-dir "D:\\Log PLM\\extracted"
        """
    )
    
    parser.add_argument(
        "--zip-path",
        required=True,
        help="Đường dẫn đến file .zip cần giải nén"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Thư mục đích (mặc định là cùng thư mục với file zip)"
    )
    
    args = parser.parse_args()
    
    print_progress("\n" + "="*60)
    print_progress("EXTRACT TEST LOGS SCRIPT")
    print_progress("="*60 + "\n")
    
    # Kiểm tra file zip
    if not validate_zip_file(args.zip_path):
        sys.exit(1)
    
    # Giải nén
    output_dir = extract_zip(args.zip_path, args.output_dir)
    
    # In tóm tắt
    print_summary(args.zip_path, output_dir)
    
    # Return code
    sys.exit(0 if output_dir else 1)


if __name__ == "__main__":
    main()
# 📚 Knowledge Base Index
# Cập nhật file này mỗi khi thêm article mới.
# Agent đọc file này ĐẦU TIÊN để tìm article phù hợp.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CÁCH DÙNG:
#   1. Agent đọc INDEX.md → tìm article liên quan
#   2. Agent đọc article cụ thể → lấy kiến thức
#   3. Agent áp dụng kiến thức vào phân tích
#
# CÁCH THÊM ARTICLE MỚI:
#   1. Tạo file .md trong folder category phù hợp
#   2. Dùng template ở cuối file này
#   3. Thêm dòng vào bảng bên dưới
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Category: os_internals (Kiến thức OS / Kernel)

| ID | File | Topic | Tags | Khi nào Agent cần đọc |
|----|------|-------|------|-----------------------|
| OS-001 | [cpu_scheduling.md](os_internals/cpu_scheduling.md) | Linux CFS, priority, nice, cgroups | `Runnable`, `priority`, `scheduling`, `CFS` | Khi Runnable tăng hoặc priority bất thường |
| OS-002 | [memory_management.md](os_internals/memory_management.md) | Pages, LMK, MemFree vs MemAvailable | `MemFree`, `MemAvailable`, `PSS`, `LMK`, `swap` | Khi memory metrics bất thường |
| OS-003 | [io_and_storage.md](os_internals/io_and_storage.md) | Block I/O, D-state, page cache, readahead | `D-state`, `Uninterruptible Sleep`, `block_io`, `pagecache` | Khi D-state / Block I/O tăng |

## Category: android_framework (Android Framework)

| ID | File | Topic | Tags | Khi nào Agent cần đọc |
|----|------|-------|------|-----------------------|
| AF-001 | [app_launch_internals.md](android_framework/app_launch_internals.md) | Zygote fork, bindApplication, Activity lifecycle | `Cold`, `Warm`, `Hot`, `Zygote`, `bindApplication`, `activityStart` | Khi phân tích app launch sequence |
| AF-002 | [binder_ipc.md](android_framework/binder_ipc.md) | Binder mechanism, sync/async, transaction | `binder`, `Sleeping`, `transaction` | Khi binder count bất thường |

## Category: profiling_tools (Công cụ & Phương pháp)

| ID | File | Topic | Tags | Khi nào Agent cần đọc |
|----|------|-------|------|-----------------------|
| PT-001 | [perfetto_guide.md](profiling_tools/perfetto_guide.md) | Perfetto trace, SQL query, slices, counters | `trace`, `perfetto`, `SQL`, `TraceProcessor` | Khi cần giải thích data source |

---

## Template cho article mới

Khi thêm article, dùng format sau:

```markdown
---
id: [CATEGORY_PREFIX]-[NUMBER]
title: [Tiêu đề ngắn gọn]
category: [os_internals | android_framework | profiling_tools | optimization | ...]
tags: [tag1, tag2, tag3]
sources:
  - [URL nguồn chính thống 1]
  - [URL nguồn chính thống 2]
last_updated: [YYYY-MM-DD]
---

# [Tiêu đề]

## Tóm tắt (3-5 câu)
[Agent đọc phần này nếu chỉ cần overview nhanh]

## Khái niệm chi tiết
[Giải thích deep, có diagram nếu cần]

## Liên hệ với Performance Analysis
[Phần này RẤT QUAN TRỌNG – nối lý thuyết với metrics thực tế]
- Metric X liên quan thế nào
- Khi nào hiện tượng này xảy ra
- Dấu hiệu nhận biết trong data

## Ví dụ thực tế
[Case study hoặc ví dụ từ project]
```

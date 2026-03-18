# Metric Glossary – App Launch Performance

## Timing Metrics (sequence)

| Metric | Đơn vị | Mô tả |
|--------|--------|-------|
| **App Execution Time** | ms | Tổng thời gian launch: Touch Down → End (activityIdle/Animating) |
| **Touch Down ~ Start Proc** | ms | Thời gian từ touch event → system bắt đầu khởi tạo process |
| **Start Proc** | ms | Thời gian system thực hiện process start |
| **Activity Thread Main** | ms | Thời gian init main thread của app |
| **Bind Application** | ms | Binding app vào runtime – **Cold launch only** |
| **Activity Start** | ms | Tạo Activity (onCreate, onStart) |
| **Activity Resume** | ms | Resume Activity (onResume) |
| **Choreographer** | ms | First frame rendering (Choreographer#doFrame) |
| **ActivityIdle** | ms | System xác nhận app đã hoàn tất launch |
| **ActivityIdle ~ Animating end** | ms | Animation sau khi idle |

## Thread States

| State | Viết tắt | Mô tả | Nguyên nhân phổ biến khi tăng |
|-------|----------|-------|-------------------------------|
| **Running** | R | Thread đang chạy trên CPU | App computation tăng, compiler type không tối ưu |
| **Runnable** | R+ | Thread sẵn sàng nhưng chờ CPU slot | CPU bận bởi process khác, priority thấp |
| **Sleeping** | S | Thread đang ngủ (voluntary wait) | Binder calls, lock contention, I/O wait |
| **Uninterruptible Sleep** | D | Blocked I/O (disk read/write) | Đọc APK, memory thiếu → swap, pageboost kém |

## LoadApkAsset

| Property | Mô tả |
|----------|-------|
| **Định nghĩa** | Thời gian AssetManager mở, parse và nạp cấu trúc file APK vào bộ nhớ |
| **Chi tiết** | Đọc bảng resources.arsc (Android Resource Table) và mmap vào RAM để app tra cứu nhanh resource IDs (R.string..., R.layout...) |
| **Đơn vị** | ms (millisecond) |
| **Giai đoạn xảy ra** | Cold Start, bên trong bindApplication, trước Activity#onCreate |
| **Process liên quan** | Chủ yếu là App Process (main thread), có thể có system processes (system_server, system_ui) |
| **Threshold để flag** | > 50ms |
| **Nguyên nhân phổ biến** | |
| - resources.arsc quá lớn | App chứa quá nhiều strings, colors, multi-language configs không cần thiết |
| - Quá nhiều Split APKs | App Bundle bị chia thành hàng chục splits → phải parse từng file riêng |
| - Disk I/O bottleneck | Memory shortage → cache bị xóa → phải đọc từ disk vật lý |
| - Pageboost kém | Pageboost miss hoặc tắt → không có prefetch → Major Page Fault |
| **Impact** | LoadApkAsset cao → Increased Uninterruptible Sleep (D-state) → Total App Launch Time tăng |
| **Team routing** | System Team |

## System Metrics

| Metric | Đơn vị | Mô tả | Threshold để flag |
|--------|--------|-------|-------------------|
| **uptime_minutes** | phút | Thời gian device đã bật trước test | > 10 phút = invalid |
| **compiler** | string | App compilation type | "verify" = chưa optimize |
| **MemFree_MB** | MB | RAM free | REF - DUT > 50MB |
| **MemAvailable_MB** | MB | RAM available (bao gồm cache) | REF - DUT > 50MB |
| **App_PSS_MB** | MB | Proportional Set Size (memory usage) | DUT - REF > 50MB |
| **Pageboostd_MB** | MB | Lượng data Pageboost đã prefetch | REF - DUT > 10MB |

## Compiler Types

| Type | Mô tả | Performance Impact |
|------|-------|-------------------|
| **speed** | AOT compile toàn bộ | Nhanh nhất, nhưng install lâu |
| **speed-profile** | AOT compile hot methods (PGO) | Cân bằng tốt nhất |
| **verify** | Chỉ verify bytecode, interpret runtime | Chậm nhất – cần upgrade |

## Binder Transaction

| Metric | Mô tả |
|--------|-------|
| **count** | Số lượng IPC calls giữa app process và system services |
| **duration_ms** | Tổng thời gian tất cả binder calls |

> Count tăng → app gọi quá nhiều system services → Sleeping time tăng.

## Priority Values

| Priority | Level | Context |
|----------|-------|---------|
| **100** | Realtime | Audio/Video threads |
| **110** | Foreground | App main thread đang visible |
| **120** | Default | Chưa được boost hoặc đang bind |
| **130** | Background | Không visible |
| **140+** | Low priority | Cached processes |

> Priority thấp hơn (số lớn hơn) = dễ bị preempt bởi thread khác → Runnable time tăng.

## Frequency Values

Đơn vị **MHz**. Ví dụ cho device thường thấy:

| Frequency | Cluster | Note |
|-----------|---------|------|
| 2400 | Big/Prime | Max performance |
| 2288 | Big | High |
| 2002 | Big | Medium |
| 1800 | Mid | Mid cluster max |
| < 1000 | Little | Power saving |

> DUT chạy ít thời gian ở max frequency hơn REF → Running time tăng dù cùng workload.

## Process Names (Truncated)

Perfetto trace thường truncate process names. Các mapping phổ biến:

| Truncated | Full Name |
|-----------|-----------|
| `ndroid.systemui` | `com.android.systemui` |
| `id.app.launcher` | `com.sec.android.app.launcher` |
| `droid.gallery3d` | `com.sec.android.gallery3d` |
| `.apps.messaging` | `com.google.android.apps.messaging` |
| `d.process.acore` | `android.process.acore` |
| `id.gms.unstable` | `com.google.android.gms.unstable` |
| `.gms.persistent` | `com.google.android.gms.persistent` |
| `popupcalculator` | `com.sec.android.app.popupcalculator` |
| `.provider.badge` | `com.samsung.android.provider.badge` |
| `composer@2.4-se` | `android.hardware.graphics.composer@2.4-service` |

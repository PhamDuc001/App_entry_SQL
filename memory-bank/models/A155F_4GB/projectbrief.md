# Project Brief — Android App Launch Performance (Multi-Model + Variant)

## Mục tiêu
Theo dõi và so sánh hiệu suất khởi động app Android qua nhiều DUT,
nhiều model, và nhiều RAM variant để phát hiện regression và đặc tính từng cấu hình.

## Models & Variants

| Model | Variant | Chipset | DUT prefix | Notes |
|-------|---------|---------|------------|-------|
| A266B | 4GB     |         | ZA         |       |
| A266B | 6GB     |         | ZA         |       |
| A165F | 4GB     |         | ZA         |       |
| A075F | 4GB     |         | ZA         |       |
| A155F | 6GB     |         | ZC         |       |

## Quy tắc phân biệt variant
- Cùng model, khác RAM = tách biệt hoàn toàn trong memory bank
- Thư mục: [MODEL]_[VARIANT], ví dụ A266B_4GB
- JSON key: "model" + "variant" cả hai đều bắt buộc

## Apps
- Calendar (com.android.calendar)
- Camera (com.sec.android.app.camera)
- Clock (com.sec.android.app.clockpackage)
- Message (com.samsung.android.messaging)
- Gallery (com.sec.android.gallery3d)

## Launch types
- Cold: bindApplication → activityIdle
- Warm: resume từ memory

## Ngưỡng đánh giá (DUT - REF)
| Metric group              | Regression | Improvement |
|---------------------------|------------|-------------|
| Timeline / Thread states  | > +10ms    | < -10ms     |
| Uninterruptible Sleep     | > +30ms    | < -30ms     |
| Block I/O / Binder / APK  | > +50ms    | < -50ms     |

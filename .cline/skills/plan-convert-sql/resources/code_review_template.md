# Code Review Template

> Template đánh giá code khi Agent review hoặc đề xuất thay đổi.

## File: `[filename]`

### Summary
- **Mục tiêu thay đổi:** [1 dòng]
- **Số files thay đổi:** [N]
- **Độ phức tạp:** [Thấp / Trung bình / Cao]
- **Rủi ro:** [Thấp / Trung bình / Cao]

### Changes

| # | File | Vị trí | Thay đổi | Lý do |
|---|------|--------|----------|-------|
| 1 | `file.py` | Lines X-Y | [Mô tả ngắn] | [Tại sao] |

### Checklist

**Correctness**
- [ ] Logic đúng với yêu cầu
- [ ] Edge cases (None, empty, 0) được xử lý
- [ ] Variable scope đúng
- [ ] Type đúng (str/int/float)

**Performance**
- [ ] Không có I/O trong vòng lặp thừa
- [ ] Không tạo object/list lặp lại
- [ ] Algorithm complexity hợp lý

**Safety**
- [ ] Error handling đầy đủ
- [ ] Backward compatible
- [ ] Không ghi đè data volit

### Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| [Risk 1] | [Low/Med/High] | [Cách phòng tránh] |

### Test Plan

- [ ] Test A: [Mô tả]
- [ ] Test B: [Mô tả]

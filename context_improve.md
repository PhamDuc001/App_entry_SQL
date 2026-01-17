D:\FE\Personal\Project\Plan_convert_SQL\execution_sql.py
Hiện tại, bảng Top CPU process đang lấy name theo priority là (process.name, main_thread.name, 'PID-' || process.pid). Tuy nhiên, trường hợp lấy PID-' || process.pid sẽ xảy ra trường hợp PID của DUT nằm ở process xử lý loại công việc A (đa số các app sẽ có) nhưng của REF lại trùng hợp cũng có PID này nhưng xử lý loại công việc khác dẫn đến khi tính diff vẫn tính được nhưng nội dung mang lại là vô nghĩa. Tôi muốn thay vì sử dụng PID và hiện lên bảng exel thì sẽ map PID này với tên process owner PID dựa theo file dumpstate. Để hiểu rõ hơn về cách tìm được file dumpsate, tôi sẽ trình bày cấu trúc của DUT folder (REF folder cũng tương đương):
Folder test chứa các file .log và .zip, được sinh ra trong quá trình chạy test theo cycle, với đặc điểm:
Tên file luôn chứa timestamp
Khi sort theo tên file (lexicographically) → thứ tự thời gian hoàn toàn chính xác
File .log ghi lại log entry / re-entry của app  (có dạng như sau: A576BYK7_BOS_251128_251128_085009_camera.log)
File .zip là Bugreport, xuất hiện sau khi kết thúc một nhóm log, chứa thông tin tổng hợp.
Nội dung bên trong file .zip

File .zip chứa nhiều file .txt, trong đó: dumpstate-2025-11-28-08-51-23.txt
Là file quan trọng nhất và luôn luôn có dung lượng lớn nhất (đặc điểm để tìm được chính xác file này trong folder zip khi giải nén mà không bị nhầm file .txt khác). Nó chứa full system dump / trạng thái hệ thống

Folder cha (folder truyền vào) có thể có nhiều cycle (thường là 3)  Trong mỗi cycle:
Chia thành 6 group, mMỗi group: Test 2 / 3 / 4 app, mỗi app có entry + re-entry
Test_Result_Folder/
├── A576BYK7_BOS_251128_251128_085001_camera.log
├── A576BYK7_BOS_251128_251128_085015_camera.log
├── A576BYK7_BOS_251128_251128_085030_gallery.log
├── A576BYK7_BOS_251128_251128_085045_gallery.log
├── A576BYK7_BOS_251128_251128_085059_maps.log
├── A576BYK7_BOS_251128_251128_085112_maps.log
├── A576BYK7_BOS_251128_251128_085123_1part_Bugreport.zip

├── A576BYK7_BOS_251128_251128_085200_music.log
├── A576BYK7_BOS_251128_251128_085215_music.log
├── A576BYK7_BOS_251128_251128_085230_youtube.log
├── A576BYK7_BOS_251128_251128_085245_youtube.log
├── A576BYK7_BOS_251128_251128_085259_2part_Bugreport.zip
...

Execution_sql hiện tại đang xử lý các file .log để sử dụng SQLite đọc nó (chưa có dùng đến file dumpstate) Bây giờ tôi muốn sử dụng file dumpstate.txt (trong .zip sau giải nén) như sau:
- Trong file dumpstate, tìm đến phần "Total PSS by process:" có nội dung dạng như sau:
Total PSS by process:
    314,911K: com.android.systemui (pid 2009)                             (   26,367K in swap)
    276,444K: system (pid 1335)                                           (   23,311K in swap)
    219,752K: com.sec.android.app.launcher (pid 2806 / activities)        (   17,672K in swap)
    182,059K: surfaceflinger (pid 1006)                                   (   36,180K in swap)
     73,464K: com.samsung.android.honeyboard (pid 4350)                   (    6,980K in swap)
     67,343K: com.samsung.android.smartsuggestions (pid 3601)             (    5,472K in swap)
     59,349K: com.samsung.android.smartsuggestions:search (pid 3902)      (   13,360K in swap)

Total PSS by OOM adjustment:
    649,176K: Native                                                      (  261,292K in swap)
    .....
(Lưu ý: giữa Total PSS by process và Total PSS by OOM adjustment có 1 dòng khoảng cách để tách hai phần)
Ví dụ tại dòng 314,911K: com.android.systemui (pid 2009)                             (   26,367K in swap)
sẽ phải detect được pid 2009 tương ứng với process name là com.android.systemui để cho dù trong folder REF có trùng PID 2009 nhưng khác process name thì sẽ không tính vào.
Hãy đọc yêu cầu của tôi cẩn thận để đảm bảo hiểu 100%, nếu có gì thắc mắc hãy hỏi tôi ngay.
Hãy lên kế hoạch chi tiết để implement theo yêu cầu trên, tôi sẽ đợi kế hoạch của bạn để tôi có thể lên kế hoạch chi tiết cho phần cải tiến của tôi
Ngoài ra, tôi có một vài exception case cần bạn xem xét (có thể xử lý sau khi cải tiến này hoàn thành):
1. Sau khi kết thúc một nhóm log, có log entry/re-entry của app nhưng thiếu file .Zip
=> Tôi đang có solution là sẽ đếm: Vì một nhóm test chỉ có tối đa 4 apps, nên nếu file .log đang xử lý nằm ở app thứ 5 mà trước đó chưa đọc đến file .zip  chứng tỏ nhóm test thiếu .zip (không thể biết chính xác pid nào tương ứng với process nào)
2. Folder cha (DUT, REF)truyền vào có thể có .zip, có thể chỉ có các folder (được giải nẽn sẵn và xóa hết file .zip rồi), hoặc lẫn cả folder .zip và folder đã giải nén.
=> Hiện tôi chưa có solution nào, có thể xử lý sau hoặc bạn đưa ra ý tưởng
- 
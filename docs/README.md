# TỔNG MỤC TÀI LIỆU DỰ ÁN MEP ONEAI SYSTEM

Thư mục tài liệu này đã được tinh gọn và quy hoạch thành **5 BỘ TÀI LIỆU MASTER HOÀN CHỈNH**, bao quát 100% tất cả các khía cạnh từ hướng dẫn thực chiến từng bước cho người mới, kiến trúc toàn cảnh, giải thích từng file & luồng dữ liệu, hướng dẫn triển khai thực tế, đến giải mã code của sếp và thuật toán thị giác máy tính:

---

### 🌟 [5. Cẩm Nang Thực Chiến Từng Bước: Từ Code AI Local Lên Màn Hình OneAI](./05_HUONG_DAN_CHI_TIET_TU_CODE_LOCAL_LEN_ONEAI_STEP_BY_STEP.md) 🚀 *(DÀNH CHO NGƯỜI CHƯA LÀM BAO GIỜ - COOKBOOK)*
* **Tên file:** `05_HUONG_DAN_CHI_TIET_TU_CODE_LOCAL_LEN_ONEAI_STEP_BY_STEP.md`
* **Nội dung:** Bản đồ thực thi chi tiết cầm tay chỉ việc:
  * Điểm xuất phát: Trong tay chỉ có 5 file code AI chạy local terminal.
  * **Bước 0:** Cách phân tích bài toán để xác định danh sách các cột/trường hiển thị trên màn hình.
  * **Bước 1:** Thiết kế bảng Oracle DB `create_table.sql` và thao tác trên DBeaver.
  * **Bước 2:** Cấu hình truy vấn tĩnh OneAI Gateway `mep_payment_analysis.py` (Bind Variable, phân trang `ROW_NUMBER()`).
  * **Bước 3:** Đóng gói API Javascript `mep_payment.js` gọi Gateway `/crud/ui`.
  * **Bước 4:** Xây dựng màn hình Vue 3 Dark Theme (`main.vue`, `tab/operation.vue`), cơ chế Insert vào cuối bảng (`push`), tính STT tự động, khóa timer Polling khi đang nhập, phòng thủ chống trùng mã `KEYID`.
  * **Bước 5:** Dựng máy chủ FastAPI Worker (`main.py`, `api.py`, `sql.py`) xử lý ngầm bằng `BackgroundTasks` và đóng gói `.zip` lách tường lửa DLP.
  * **Bước 6:** Tích hợp 5 file AI lõi vào Background Task.
  * **Bước 7 & Cạm bẫy:** Checklist kiểm thử từng bước và bảng tổng hợp 6 cạm bẫy kinh điển (trùng mã `KEYID`, lỗi mật khẩu `0x939`, timer 10s xóa RAM, quên `commit()`...).

---

### 📕 [4. Kiến Trúc Toàn Cảnh & Giải Mã Toàn Bộ Luồng Liên Kết Hệ Thống](./04_KIEN_TRUC_TOAN_CANH_VA_LUONG_DU_LIEU_CHI_TIET.md) ⭐ *(TÀI LIỆU QUAN TRỌNG NHẤT ĐỂ ĐI BÁO CÁO SẾP)*
* **Tên file:** `04_KIEN_TRUC_TOAN_CANH_VA_LUONG_DU_LIEU_CHI_TIET.md`
* **Nội dung:** Được biên soạn dưới góc nhìn của Senior System & Solution Architect:
  * **Bức tranh toàn cảnh 4 tầng (4-Tier Enterprise Architecture):** OneAI Vue Frontend $\rightarrow$ OneAI Gateway (`/crud/ui`) $\rightarrow$ FastAPI Worker (:8000) $\rightarrow$ Oracle DB 19c (`LOCAL_AI`).
  * **Từ điển từng file trong hệ thống:** Giải thích cặn kẽ từng file làm gì, vì sao phải có, kết nối với ai (Nhóm Core Pipeline: `config`, `utils`, `pdf_extractor`, `excel_reconciler`, `engine`; Nhóm Worker: `main`, `api`, `sql`; Nhóm OneAI: `create_table.sql`, `mep_payment_analysis.py`, `mepPayment.js`, `operation.vue`).
  * **Ma trận dòng chảy dữ liệu End-to-End:** 4 Sequence diagram chi tiết từng bước (Tải phân trang, CRUD Insert/Edit/Delete/Save, Upload kích hoạt AI ngầm, Tải file báo cáo Blob ZIP).
  * **Giải mã các quyết định kỹ thuật cốt lõi:** Tại sao cần 2 Backend? Tại sao dùng `BackgroundTasks`? Bản chất lỗi `DPY-3015: password verifier 0x939` và cơ chế cứu cánh của `Oracle Thick Client` (`oci.dll`). Vì sao phải nén `.zip` lách tường lửa DLP?
  * **Kịch bản thuyết minh bảo vệ dự án trước Sếp:** Bài nói 2 phút (Elevator Pitch), kịch bản Demo trực tiếp và bộ câu hỏi vấn đáp hóc búa từ Sếp kèm câu trả lời mẫu chuẩn Senior Architect.

---

### 📘 [1. Hướng Dẫn Triển Khai OneAI Toàn Diện](./01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md)
* **Tên file:** `01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md`
* **Nội dung:** Cuốn cẩm nang thi công trọn gói từ A-Z:
  * Toàn bộ mã nguồn DDL tạo bảng Oracle Database (`LOCAL_AI.MEP_PAYMENT_ANALYSIS`).
  * Cấu hình OneAI Backend QuerySettings (`mep_payment_analysis.py`).
  * Cấu hình Javascript gọi Gateway OneAI (`mepPayment.js`).
  * Giao diện hoàn chỉnh Vue 3 Element Plus Dark Theme (`MepOperation.vue`) tích hợp Toolbar chuẩn OneAI: **Delete, Insert, Export, Save**, Checkbox chọn dòng, ô gõ inline trực tiếp và hàm tải file Blob download chống chặn mạng nội bộ.
  * Dịch vụ Worker chạy ngầm (`api.py` & `sql.py`) tự động đóng gói file báo cáo `.zip` lách hệ thống bảo mật DLP doanh nghiệp.
  * Quy trình dọn dẹp ảnh bằng chứng tự động định kỳ 15–30 ngày.

---

### 📗 [2. Giải Mã Toàn Diện Mã Nguồn Của Sếp](./02_GIAI_MA_TOAN_DIEN_CODE_SEP_GUI.md)
* **Tên file:** `02_GIAI_MA_TOAN_DIEN_CODE_SEP_GUI.md`
* **Nội dung:** Bản phân tích sâu sắc về file `Sepgui.xlsx`:
  * Trả lời trực diện các câu hỏi: Có phải sếp đổi hướng không? Có phải bỏ code của mình không? Tại sao sếp cần 25 file?
  * Bản chất dự án `wo-check` của sếp (Ứng dụng web độc lập Standalone vs Plugin cắm giắc vào OneAI).
  * Sơ đồ luồng hoạt động tổng thể của code sếp bằng Mermaid.
  * Phân tích chi tiết 100% từng file trong 25 file của sếp.
  * Ý nghĩa 3 file test mẫu (`WO-TEST-001`, `002`, `003`) và script vẽ PDF giả lập `tao_file_mau.py`.
  * Bảng đối chiếu chéo 1-1 và kịch bản đối thoại tự tin bảo vệ giải pháp trước sếp.

---

### 📙 [3. Thuật Toán Lõi & Kiến Trúc Pipeline](./03_THUAT_TOAN_LOI_PIPELINE_ARCHITECTURE.md)
* **Tên file:** `03_THUAT_TOAN_LOI_PIPELINE_ARCHITECTURE.md`
* **Nội dung:** Tài liệu chuyên sâu về mặt kỹ thuật thuật toán toán học và xử lý hình ảnh:
  * Trạm điều phối đa luồng `engine.py`.
  * Thuật toán OpenCV Magic Crop, bộ lọc hình thái học (Morphological Kernels 50x1), phát hiện viền bảng (Bounding Box).
  * Kỹ thuật RAM Chunking băm ảnh, loại bỏ nét vẽ CAD thừa, prompt AI Vision chống ảo giác (Zero Hallucination).
  * Động cơ Calamine Rust quét Radar động 20 dòng đầu file Vendor Excel.
  * Thuật toán đối soát 2 Vòng (Bản vẽ + Gate Pass), tổ hợp khóa 3 chiều (Code + Phụ trội % + Remark), và định dạng tô màu tự động bằng OpenPyXL.

---

### 📐 [6. Kiến Trúc & Kế Hoạch Triển Khai Step 2: MEP CAD Vector Engine](./06_KIEN_TRUC_STEP2_BOC_TACH_CAD_DXF_VA_DOI_SOAT_SO_DO_DI_DAY.md) 🚀 *(ĐỐI SOÁT HÌNH HỌC THIẾT KẾ CAD DXF VS EXCEL STEP 1)*
* **Tên file:** `06_KIEN_TRUC_STEP2_BOC_TACH_CAD_DXF_VA_DOI_SOAT_SO_DO_DI_DAY.md`
* **Nội dung:** Toàn bộ chiến lược và phương pháp triển khai Step 2:
  * **Hiện trạng AI thị giác toàn cầu:** Lý do chưa có AI nào nhìn ảnh bản vẽ A0 mà bóc tách chuẩn 100% (nút thắt Gigapixel, nhiễu hình học) và cách các tập đoàn lớn (Autodesk, Trimble, Glodon) giải quyết.
  * **Chiến lược triển khai On-Premise nội bộ:** Mô hình Hybrid kết hợp **Python ezdxf** (đo đạc hình học vector chính xác 100%, 0% GPU) và **Qwen 3.8 NextAI** (đọc hiểu ngữ nghĩa ghi chú kỹ thuật sang JSON).
  * **Giải mã quy chuẩn ký hiệu (Symbol Key & Legend):** Phân tích bảng ký hiệu chuẩn có sẵn trên bản vẽ thực tế `img1.png`, `img2.png` (`SPARE CABLE`, `CABLE LINE UP/DN`, `STEEL CONDUIT`, `FLEXIBLE CONDUIT`, `CABLE DUCT & TRAY`) và cách lưu trữ trong CAD (Layer, Linetype, Lineweight, Text tags `22C`).
  * **Kịch bản dự phòng khi KHÔNG CÓ CAD:** Quy trình 5 bước Computer Vision (OpenCV Crop bảng chú giải, lọc hình thái học nét đậm, vector hóa Skeletonization, đo tỷ lệ pixel theo trục cột `9,000` mm, Qwen 3.8 đọc cao độ `UP/DN`).
  * **Ma trận yêu cầu hai bên:** Chuẩn hóa Layer & Block cho nhà thầu, xây dựng 4 module cho đội ngũ phát triển, thuật toán Python mẫu và lộ trình 4 tuần.

---

### 🎨 [7. Nâng Cấp Giao Diện Trực Quan 4 Tab Theo Chuẩn Sếp Gửi](./07_KIEN_TRUC_NANG_CAP_GIAO_DIEN_TRUC_QUAN_THEO_CHUAN_SEP_GUI.md) ⚡ *(PHIÊN BẢN MỚI NHẤT - LATEST)*
* **Tên file:** `07_KIEN_TRUC_NANG_CAP_GIAO_DIEN_TRUC_QUAN_THEO_CHUAN_SEP_GUI.md`
* **Nội dung:** Toàn bộ giải pháp nâng cấp giao diện trực quan và trải nghiệm người dùng (UX):
  * **Hệ thống 5 Thẻ KPI:** Tổng hồ sơ, Khớp 100%, Có sai lệch, Đang đối soát, Chờ duyệt (Click-to-filter nhanh danh sách).
  * **Hộp thoại Đối soát 4 Tab (Modal Dialog):** 
    - Tab 1: Danh sách chi tiết lỗi sai lệch (Bản vẽ, Mã SDAC, Tên vật tư, SL Dự toán, SL Bản vẽ, Chênh lệch).
    - Tab 2: Đối chiếu gom nhóm theo từng Bản vẽ kỹ thuật (Accordion đa tầng).
    - Tab 3: Băng chuyền soi ảnh bản vẽ & xem phóng to độ phân giải cao (Lightbox SVG/PNG).
    - Tab 4: Console hiển thị nhật ký bóc tách của AI theo thời gian thực.
  * **Quy trình Phê duyệt & Chạy lại AI (Rerun):** Kỹ sư nhập ghi chú nghiệm thu, bấm Duyệt (Approve) hoặc Từ chối (Reject), và kích hoạt Chạy lại AI (Rerun) ngay trong modal hoặc khi tác vụ thất bại.
  * **Phân tách sự kiện triệt để (Không xung đột):** Gỡ bỏ `@row-dblclick` để bảo toàn tính năng click đúp sửa inline các ô Part/Group/Task Name, mở modal chỉ bằng click chuột trái vào Số WO hoặc Kết quả kiểm tra.
  * **Sửa lỗi STT phân trang:** Công thức `nextStt` toàn cục đảm bảo thêm dòng mới ở bất kỳ trang nào cũng mang số thứ tự tiếp theo chính xác.
  * **Danh mục tối giản:** Chỉ cần sửa duy nhất 3 file (`detail_builder.py`, `api.py`, `operation.vue`), giữ nguyên 100% logic thuật toán lõi.

---

> 📂 **Thư mục lưu trữ lịch sử:** Các bản nháp hoặc tài liệu đơn lẻ trước đây đã được lưu trữ an toàn trong thư mục [`archive/`](./archive/) để tra cứu khi cần thiết.

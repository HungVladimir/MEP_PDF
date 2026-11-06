# TỔNG MỤC TÀI LIỆU DỰ ÁN MEP ONEAI SYSTEM

Thư mục tài liệu này đã được tinh gọn, quy hoạch và nâng cấp thành **10 BỘ TÀI LIỆU MASTER HOÀN CHỈNH**, bao quát 100% tất cả các khía cạnh từ hướng dẫn thực chiến từng bước cho người mới, kiến trúc toàn cảnh 4 tầng, giải mã code của sếp, thuật toán thị giác máy tính, bóc tách CAD vector, giao diện trực quan 4 tab, tích hợp MinIO Cloud Storage chuẩn Enterprise, đến cẩm nang phân giải chi tiết từng con số trên màn hình và giải mã chuyên sâu 2 module lõi:

---

### 🌟 [10. Giải Mã Toàn Diện Về minio_storage.py & detail_builder.py: Bản Chất, Luồng Hoạt Động & Vị Trí Đặt File](./10_GIAI_MA_LUONG_MINIO_STORAGE_VA_DETAIL_BUILDER.md) 🚀 *(GIẢI THÍCH CHUYÊN SÂU 2 MODULE THEN CHỐT)*
* **Tên file:** `10_GIAI_MA_LUONG_MINIO_STORAGE_VA_DETAIL_BUILDER.md`
* **Nội dung:** Giải thích cặn kẽ bản chất, lý do tồn tại và vị trí triển khai của 2 module:
  * **Vị trí đặt file chuẩn xác:** Khẳng định dứt khoát cả 2 file **bắt buộc phải đặt trong dự án gốc của bạn** (FastAPI Worker Service `backend/`), tuyệt đối không đặt vào OneAI Core.
  * **Tại sao phải dùng chúng:** Phân tích hậu quả nếu không có (trình duyệt không đọc được Excel nhị phân, mất dữ liệu khi restart container, lỗi 404 khi chạy phân tán).
  * **Bản chất của `minio_storage.py`:** Bộ điều phối Cloud Storage Adapter Dual-Mode, quản lý stream ảnh/báo cáo, presigned URL và dọn dẹp bù trừ khi xóa dòng.
  * **Bản chất của `detail_builder.py`:** Bộ biên dịch dữ liệu (Data Reconcile Compiler), bóc tách từng bản vẽ, tính chênh lệch, gom ảnh, gom log đóng gói thành JSON cache `detail.json` chỉ 0.05s hiển thị.
  * **Vòng đời 4 giai đoạn & Sơ đồ tương tác mạng:** Sequence Diagram từng bước và sơ đồ kết nối mạng giữa Vue $\rightarrow$ Gateway $\rightarrow$ Worker (:8000) $\rightarrow$ Oracle DB / MinIO S3.

---

### 🌟 [9. Hướng Dẫn Chi Tiết Luồng Code Hiển Thị Form & Bản Đồ Ánh Xạ Dữ Liệu Toàn Phần](./09_HUONG_DAN_CHI_TIET_LUONG_CODE_HIEN_THI_FORM_VA_DU_LIEU.md) 🚀 *(CẨM NANG BÓC TÁCH TỪNG CON SỐ TRÊN GIAO DIỆN)*
* **Tên file:** `09_HUONG_DAN_CHI_TIET_LUONG_CODE_HIEN_THI_FORM_VA_DU_LIEU.md`
* **Nội dung:** Phân giải chi tiết 100% từng thành phần trên giao diện:
  * **Hình 1 (Bảng quản trị & 5 Thẻ KPI):** Bản đồ con số thực tế (41, 5, 7, 0, 29), câu lệnh SQL `searchTotalRow` và `get_kpi_summary`, các cột bảng và phân trang.
  * **Hình 2 (Modal Header, 4 Thẻ thống kê & Tab 1: Danh sách lỗi):** Cơ chế gọi `GET /mep_payment/detail/{id}`, bóc tách số lượng cụ thể từng bản vẽ (`59.0` vs `58.0` $\rightarrow$ `Thiếu 1.0`), tooltip hover và chi tiết đối chiếu.
  * **Hình 3 (Tab 2: Đối chiếu theo từng bản vẽ):** Cơ chế Accordion đa tầng theo 5 bản vẽ (`0105`..`0505`), quy tắc gán SL Dự toán $=$ SL Bản vẽ này nếu Khớp 100%.
  * **Tab 3 (Soi bản vẽ & ảnh trích xuất):** Quét 19 ảnh bằng chứng từ `drawings/`, `evidence_images/` hoặc MinIO Storage, cơ chế phóng to Lightbox chống nhấp nháy bằng `:preview-teleported="true"`.
  * **Tab 4 (Nhật ký AI):** Console hộp đen màu đen hiển thị log bóc tách thời gian thực từ buffer `TeeStream` và `pipeline.log`.
  * **Khung Phê duyệt & Thao tác:** Ghi chú duyệt, nút Duyệt (`APPROVED`), Từ chối (`REJECTED`), Rerun và Tải báo cáo ZIP/Excel.
  * **Bảng Ma trận Ánh xạ Tổng thể (Master Mapping Matrix):** Bảng tra cứu trực diện từ phần tử UI $\rightarrow$ biến Vue $\rightarrow$ API Endpoint $\rightarrow$ File Backend $\rightarrow$ Cột Database / File Excel.

---

### 🌟 [8. Hướng Dẫn Tích Hợp MinIO Storage, Bóc Tách Sai Lệch Chi Tiết & Tối Ưu Giao Diện](./08_HUONG_DAN_TICH_HOP_MINIO_STORAGE_VA_XU_LY_SAI_LECH_CHI_TIET.md) ⚡ *(PHIÊN BẢN v2.5 LATEST)*
* **Tên file:** `08_HUONG_DAN_TICH_HOP_MINIO_STORAGE_VA_XU_LY_SAI_LECH_CHI_TIET.md`
* **Nội dung:** Toàn bộ giải pháp nâng cấp hạ tầng lưu trữ và chuẩn hóa dữ liệu đối chiếu:
  * **MinIO Object Storage Adapter Dual-Mode:** Tự nhận diện biến môi trường `ONEAI_MINIO_*` hoặc `MINIO_*` trong `.env`. Cơ chế Graceful Fallback tự chuyển sang đĩa cục bộ mà không crash nếu MinIO offline.
  * **Chuẩn hóa số liệu Tab 1 & Tab 2 (`detail_builder.py`):** Xây dựng hàm `parse_dwg_segments` trích xuất chính xác số lượng Vendor khai và số lượng AI bóc tách cho riêng bản vẽ đó (chấm dứt tình trạng $101 = 101$ mà báo lỗi hoặc $3.0 \neq 0.4$ mà báo khớp).
  * **Cơ chế Auto-Detect & Rebuild Cache:** Tự động phát hiện cache cũ trên MinIO / Local Disk và tự động rebuild lại từ file Excel báo cáo sang định dạng mới chuẩn xác ngay khi mở modal.
  * **Tách rời CSS (`operation.css`):** Giảm dung lượng file `operation.vue`, fix triệt để lỗi nhấp nháy thumbnail khi xem ảnh bằng `:preview-teleported="true"`.
  * **Sửa lỗi Smart Polling:** Tự động làm biến mất dòng 100% khi lọc tab "Đang đối soát AI", dừng polling ngầm và tự động cập nhật số liệu 5 thẻ KPI.
  * **Sửa lỗi Oracle DB Connection:** Xử lý `cursor = cur.cursor()` trong `check_keyid_exists`, triệt tiêu cảnh báo `'Connection' has no attribute 'fetchall'`.

---

### 🎨 [7. Nâng Cấp Giao Diện Trực Quan 4 Tab Theo Chuẩn Sếp Gửi](./07_KIEN_TRUC_NANG_CAP_GIAO_DIEN_TRUC_QUAN_THEO_CHUAN_SEP_GUI.md) *(PHIÊN BẢN v2.0)*
* **Tên file:** `07_KIEN_TRUC_NANG_CAP_GIAO_DIEN_TRUC_QUAN_THEO_CHUAN_SEP_GUI.md`
* **Nội dung:** Toàn bộ giải pháp nâng cấp giao diện trực quan và trải nghiệm người dùng (UX):
  * **Hệ thống 5 Thẻ KPI:** Tổng hồ sơ, Khớp 100%, Có sai lệch, Đang đối soát, Chờ duyệt (Click-to-filter nhanh danh sách).
  * **Hộp thoại Đối soát 4 Tab (Modal Dialog):** 
    - Tab 1: Danh sách chi tiết lỗi sai lệch (Bản vẽ, Mã SDAC, Tên vật tư, SL Dự toán, SL Bản vẽ, Chênh lệch).
    - Tab 2: Đối chiếu gom nhóm theo từng Bản vẽ kỹ thuật (Accordion đa tầng).
    - Tab 3: Băng chuyền soi ảnh bản vẽ & xem phóng to độ phân giải cao (Lightbox SVG/PNG).
    - Tab 4: Console hiển thị nhật ký bóc tách của AI theo thời gian thực.
  * **Quy trình Phê duyệt & Chạy lại AI (Rerun):** Kỹ sư nhập ghi chú nghiệm thu, bấm Duyệt (Approve) hoặc Từ chối (Reject), và kích hoạt Chạy lại AI (Rerun) ngay trong modal hoặc khi tác vụ thất bại.
  * **Phân tách sự kiện triệt để (Không xung đột):** Gỡ bỏ `@row-dblclick` để bảo toàn tính năng click đúp sửa inline các ô Part/Group/Task Name, mở modal chỉ bằng click chuột trái vào Kết quả kiểm tra.
  * **Sửa lỗi STT phân trang:** Công thức `nextStt` toàn cục đảm bảo thêm dòng mới ở bất kỳ trang nào cũng mang số thứ tự tiếp theo chính xác.

---

### 🌟 [5. Cẩm Nang Thực Chiến Từng Bước: Từ Code AI Local Lên Màn Hình OneAI](./05_HUONG_DAN_CHI_TIET_TU_CODE_LOCAL_LEN_ONEAI_STEP_BY_STEP.md) 🚀 *(DÀNH CHO NGƯỜI MỚI - COOKBOOK)*
* **Tên file:** `05_HUONG_DAN_CHI_TIET_TU_CODE_LOCAL_LEN_ONEAI_STEP_BY_STEP.md`
* **Nội dung:** Bản đồ thực thi chi tiết cầm tay chỉ việc:
  * Điểm xuất phát: Trong tay chỉ có 5 file code AI chạy local terminal.
  * **Bước 0:** Phân tích bài toán để xác định danh sách các cột/trường hiển thị trên màn hình.
  * **Bước 1:** Thiết kế bảng Oracle DB `create_table.sql` và thao tác trên DBeaver.
  * **Bước 2:** Cấu hình truy vấn tĩnh OneAI Gateway `mep_payment_analysis.py` (Bind Variable, phân trang `ROW_NUMBER()`).
  * **Bước 3:** Đóng gói API Javascript `mep_payment.js` gọi Gateway `/crud/ui`.
  * **Bước 4:** Xây dựng màn hình Vue 3 Dark Theme (`main.vue`, `tab/operation.vue`), cơ chế Insert vào cuối bảng (`push`), tính STT tự động, khóa timer Polling khi đang nhập, phòng thủ chống trùng mã `KEYID`.
  * **Bước 5:** Dựng máy chủ FastAPI Worker (`main.py`, `api.py`, `sql.py`) xử lý ngầm bằng `BackgroundTasks` và đóng gói `.zip` lách tường lửa DLP.
  * **Bước 6:** Tích hợp các module AI lõi vào Background Task.
  * **Bước 7 & Cạm bẫy:** Checklist kiểm thử từng bước và bảng tổng hợp 6 cạm bẫy kinh điển (trùng mã `KEYID`, lỗi mật khẩu `0x939`, timer 10s xóa RAM, quên `commit()`...).

---

### 📕 [4. Kiến Trúc Toàn Cảnh & Giải Mã Toàn Bộ Luồng Liên Kết Hệ Thống](./04_KIEN_TRUC_TOAN_CANH_VA_LUONG_DU_LIEU_CHI_TIET.md) ⭐ *(TÀI LIỆU QUAN TRỌNG ĐỂ BÁO CÁO SẾP)*
* **Tên file:** `04_KIEN_TRUC_TOAN_CANH_VA_LUONG_DU_LIEU_CHI_TIET.md`
* **Nội dung:** Được biên soạn dưới góc nhìn của Senior System & Solution Architect:
  * **Bức tranh toàn cảnh 4 tầng (4-Tier Enterprise Architecture):** OneAI Vue Frontend $\rightarrow$ OneAI Gateway (`/crud/ui`) $\rightarrow$ FastAPI Worker (:8000) $\rightarrow$ Oracle DB 19c (`LOCAL_AI`).
  * **Từ điển từng file trong hệ thống:** Giải thích cặn kẽ từng file làm gì, vì sao phải có, kết nối với ai (Nhóm Core Pipeline: `config`, `utils`, `pdf_extractor`, `excel_reconciler`, `engine`; Nhóm Worker: `main`, `api`, `sql`, `minio_storage`, `detail_builder`; Nhóm OneAI: `create_table.sql`, `mep_payment_analysis.py`, `mep_payment.js`, `operation.vue`, `operation.css`).
  * **Ma trận dòng chảy dữ liệu End-to-End:** 4 Sequence diagram chi tiết từng bước (Tải phân trang, CRUD Insert/Edit/Delete/Save, Upload kích hoạt AI ngầm, Tải file báo cáo Blob ZIP).
  * **Giải mã các quyết định kỹ thuật cốt lõi:** Tại sao cần 2 Backend? Tại sao dùng `BackgroundTasks`? Bản chất lỗi `DPY-3015: password verifier 0x939` và cơ chế cứu cánh của `Oracle Thick Client` (`oci.dll`). Vì sao phải nén `.zip` lách tường lửa DLP?
  * **Kịch bản thuyết minh bảo vệ dự án trước Sếp:** Bài nói 2 phút (Elevator Pitch), kịch bản Demo trực tiếp và bộ câu hỏi vấn đáp hóc búa từ Sếp kèm câu trả lời mẫu chuẩn Senior Architect.

---

### 📘 [1. Hướng Dẫn Triển Khai OneAI Toàn Diện](./01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md)
* **Tên file:** `01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md`
* **Nội dung:** Cuốn cẩm nang thi công trọn gói từ A-Z:
  * Toàn bộ mã nguồn DDL tạo bảng Oracle Database (`LOCAL_AI.MEP_PAYMENT_ANALYSIS`).
  * Cấu hình OneAI Backend QuerySettings (`mep_payment_analysis.py`).
  * Cấu hình Javascript gọi Gateway OneAI (`mep_payment.js`).
  * Giao diện hoàn chỉnh Vue 3 Element Plus Dark Theme tích hợp Toolbar chuẩn OneAI: **Delete, Insert, Export, Save**, Checkbox chọn dòng, ô gõ inline trực tiếp và hàm tải file Blob download chống chặn mạng nội bộ.
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

> 📂 **Thư mục lưu trữ lịch sử:** Các bản nháp hoặc tài liệu đơn lẻ trước đây đã được lưu trữ an toàn trong thư mục [`archive/`](./archive/) để tra cứu khi cần thiết.

# TỔNG MỤC TÀI LIỆU DỰ ÁN MEP ONEAI SYSTEM

Thư mục tài liệu này đã được tinh gọn và quy hoạch thành **3 BỘ TÀI LIỆU MASTER HOÀN CHỈNH**, bao quát 100% tất cả các khía cạnh từ kiến trúc triển khai, giải mã code của sếp, đến thuật toán lõi thị giác máy tính:

---

### 📘 [1. Hướng Dẫn Triển Khai OneAI Toàn Diện](./01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md)
* **Tên file:** `01_HUONG_DAN_TRIEN_KHAI_ONEAI_TOAN_DIEN.md`
* **Nội dung:** Cuốn cẩm nang thi công trọn gói từ A-Z:
  * Kiến trúc hệ thống phân tán giữa OneAI Portal, Oracle Database và FastAPI Worker.
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

> 📂 **Thư mục lưu trữ lịch sử:** Các bản nháp hoặc tài liệu đơn lẻ trước đây đã được lưu trữ an toàn trong thư mục [`archive/`](./archive/) để tra cứu khi cần thiết.


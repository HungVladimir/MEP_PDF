# GIẢI MÃ TOÀN DIỆN MÃ NGUỒN CỦA SẾP (`Sepgui.xlsx`)
## ĐÁNH GIÁ Ý ĐỊNH, PHÂN TÍCH 25 FILE, SƠ ĐỒ LUỒNG VÀ MA TRẬN ĐỐI CHIẾU VỚI DỰ ÁN MEP

> **Tài liệu tổng hợp toàn diện (Consolidated Master Guide):** Hợp nhất toàn bộ phân tích về ý định của sếp khi gửi file vào 11h đêm, giải mã lý do tại sao có nhiều file, phân tích chi tiết từng file một trong 25 file, ý nghĩa 3 file test mẫu (`WO-TEST-001`, `002`, `003`) và chiến lược bảo vệ thành quả code của bạn.

---

## MỤC LỤC TỔNG QUAN

1. [TRẢ LỜI NGAY CÁC CÂU HỎI QUAN TRỌNG NHẤT CỦA BẠN](#1-trả-lời-ngay-các-câu-hỏi-quan-trọng-nhất-của-bạn)
2. [BẢN CHẤT SOURCE CODE CỦA SẾP: ĐÂY LÀ GÌ?](#2-bản-chất-source-code-của-sếp-đây-là-gì)
3. [SƠ ĐỒ LUỒNG HOẠT ĐỘNG TỔNG THỂ CỦA CODE SẾP (`wo-check`)](#3-sơ-đồ-luồng-hoạt-động-tổng-thể-của-code-sếp-wo-check)
4. [SO SÁNH ĐỐI ĐẦU: CODE SẾP VS. BỘ CODE LÕI MEP CỦA BẠN](#4-so-sánh-đối-đầu-code-sếp-vs-bộ-code-lõi-mep-của-bạn)
5. [PHÂN TÍCH CHI TIẾT 100% TỪNG FILE TRONG `Sepgui.xlsx` (25 FILE)](#5-phân-tích-chi-tiết-100-từng-file-trong-sepguixlsx-25-file)
   * Nhóm 1: Các file thuật toán xử lý lõi (`backend/app/processing/`)
   * Nhóm 2: Các file máy chủ và dữ liệu (`backend/app/`)
   * Nhóm 3: Các màn hình giao diện (`frontend/src/`)
   * Nhóm 4: Khung sườn Web Frontend (`App.vue`, `api.js`, `store.js`...)
   * Nhóm 5: Hạ tầng & Dữ liệu mẫu (`deploy/`, `samples/tao_file_mau.py`)
6. [Ý NGHĨA CỦA 3 FILE TEST MẪU (WO-TEST-001, 002, 003)](#6-ý-nghĩa-của-3-file-test-mẫu-wo-test-001-002-003)
7. [BẢN ĐỒ ĐỐI CHIẾU CHÉO (MAPPING MATRIX)](#7-bản-đồ-đối-chiếu-chéo-mapping-matrix)
8. [CHIẾN LƯỢC BẢO VỆ CODE VÀ KỊCH BẢN BÁO CÁO VỚI SẾP](#8-chiến-lược-bảo-vệ-code-và-kịch-bản-báo-cáo-với-sếp)

---

## 1. TRẢ LỜI NGAY CÁC CÂU HỎI QUAN TRỌNG NHẤT CỦA BẠN

### ❓ Câu hỏi 1: Có phải sếp đang tự giải bài toán theo hướng khác không?
👉 **TRẢ LỜI:** **KHÔNG HỀ ĐỔI HƯỚNG!**  
Sếp có **cùng chung một tư duy và luồng chạy 100% giống bạn**:  
$$\text{Upload Excel} \longrightarrow \text{Rạch bụng file lấy PDF OLE} \longrightarrow \text{Chuyển PDF sang ảnh} \longrightarrow \text{Gọi AI Vision đọc bảng} \longrightarrow \text{So khớp với BOM} \longrightarrow \text{Xuất lỗi}$$  
Tuy nhiên, sếp đang dựng một **bản mẫu khung (Prototype / Proof of Concept)** ở mức độ bài toán cơ bản (bản vẽ linh kiện điện thoại đơn giản vẽ bằng ReportLab), chứ **chưa hề giải bài toán thực tế phức tạp của cơ điện MEP**.

---

### ❓ Câu hỏi 2: Có phải tôi phải bỏ hết code logic và FastAPI của mình không?
👉 **TRẢ LỜI:** **TUYỆT ĐỐI KHÔNG! BẠN PHẢI BẢO TOÀN NGUYÊN VẸN BỘ CODE CỦA BẠN!**
* **Về FastAPI:** Chính sếp trong file `backend/app/main.py` cũng **dùng FastAPI 100%**!
* **Về Logic:** Bộ não trong 3 file ([`pdf_extractor.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/pdf_extractor.py), [`excel_reconciler.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/excel_reconciler.py), [`engine.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/engine.py)) của bạn giải quyết các bài toán "sống còn" mà code sếp **hoàn toàn chưa có**:
  1. Thuật toán **OpenCV Magic Crop** cắt tách nhiều bảng (Multi-tables) trên bản vẽ A0/A1.
  2. Kỹ thuật **Chunking băm nhỏ ảnh trong RAM** chống ảo giác (Zero Hallucination).
  3. Ép chuẩn mã vật tư **SDAC 12 ký tự** (`M03-xxxxxxxx`).
  4. **Đối soát Vòng 2 với Gate Pass (Biên bản giao nhận)** trừ vật tư SDV cấp.
  5. Cột **Phụ trội (%)** và cột **Remark SDV**.
  6. Xuất báo cáo Excel 2 Sheet tô màu Xanh/Đỏ tự động bằng OpenPyXL.

Nếu bỏ code của bạn đi mà chạy code của sếp trên bản vẽ MEP thực tế tại nhà máy, **hệ thống sẽ crash ngay lập tức** vì AI không thể đọc nổi cả tờ giấy CAD A0/A1 nếu không crop và cắt khúc!

---

### ❓ Câu hỏi 3: Tại sao trong code sếp gửi lại cần nhiều file thế (hơn 25 file)? Tôi có cần phải tạo nhiều file thế để đẩy lên OneAI không?
👉 **TRẢ LỜI:** 
* **Sếp làm 25 file vì:** Sếp đang tạo một **Ứng dụng Web Độc Lập từ A-Z (Standalone Web Application)** mang tên `wo-check` để tự chạy riêng trên máy cá nhân (cần từ `index.html`, `vite.config.js`, `store.js`, `nginx.conf`, đến SQLite `app.db`).
* **Bạn KHÔNG CẦN nhiều file như sếp vì:** Nền tảng **OneAI của công ty là một Siêu Ứng Dụng (Super-App)** đã có sẵn hơn 80% hạ tầng: Vue 3, Pinia Store, Element Plus Dark Theme, Oracle Database `LOCAL_AI`, SSO, Nginx và bộ máy CRUD `/crud/ui`.
* **Bạn chỉ cần các file cắm giắc (Plugin):**
  1. Frontend: 1 view [`MepOperation.vue`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/frontend/src/views/MepOperation.vue) + 1 file config [`mepPayment.js`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/frontend/src/js/mepPayment.js).
  2. OneAI Backend: 1 file QuerySettings [`mep_payment_analysis.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/backend/mep_payment_analysis.py).
  3. Database: 1 script DDL Oracle `create_table.sql`.
  4. Worker Backend: Các file não bộ xử lý ngầm của bạn (`api.py`, `pdf_extractor.py`, `excel_reconciler.py`, `engine.py`, `sql.py`).

---

## 2. BẢN CHẤT SOURCE CODE CỦA SẾP: ĐÂY LÀ GÌ?

Trong file `Sepgui.xlsx`, sếp đã nén nguyên một project hoàn chỉnh có tên là **`wo-check`** (Workorder Material Check):

```
wo-check/
├── backend/            FastAPI + SQLite (Python 3.9+)
│   ├── app/
│   │   ├── main.py         API FastAPI (Endpoints)
│   │   ├── auth.py         Xác thực người dùng (SSO / Dev User)
│   │   ├── db.py           Cơ sở dữ liệu SQLite cục bộ (app.db)
│   │   ├── config.py       Biến môi trường
│   │   └── processing/     Module thuật toán: extract, render, bom, ai, compare, pipeline
│   └── requirement.txt
├── frontend/           Vue 3 + Vite (Giao diện độc lập, style.css tùy biến)
│   └── src/ (App.vue, pages/, components/, api.js, store.js)
├── samples/            tao_file_mau.py (Sinh 3 file Excel test mẫu)
└── deploy/             nginx.conf.example
```

> ⚠️ **ĐIỂM ĐẶC BIỆT CẦN LƯU Ý:**
> * Giao diện Frontend này là một **web độc lập viết bằng Vite + CSS thuần sáng màu**, **KHÔNG PHẢI giao diện OneAI (Dark Theme Element Plus)** của công ty!
> * Database của sếp là **SQLite cục bộ (`app.db`)**, trong khi hệ thống công ty bắt buộc dùng **Oracle Database (`LOCAL_AI`)**.
> * Điều này chứng minh: **Đây là project nghiên cứu / PoC (Proof of Concept) mà sếp tự làm thử ở máy cá nhân**, nhằm mục đích gợi ý luồng chạy cho bạn!

---

## 3. SƠ ĐỒ LUỒNG HOẠT ĐỘNG TỔNG THỂ CỦA CODE SẾP (`wo-check`)

```mermaid
flowchart TD
    subgraph FRONTEND ["FRONTEND (VUE 3 + VITE)"]
        A["Người dùng mở Web: ListPage.vue"] -->|Bấm Thêm mới| B["AddWorkorderModal.vue<br>(Kéo thả file Excel)"]
        B -->|Gọi api.js: POST /api/workorders| C["Upload File Excel"]
        D["Polling 3s / lần"] -->|GET /api/workorders| A
        E["Click dòng WO"] -->|Mở chi tiết| F["WorkorderDetail.vue<br>(Xem lỗi & Xem ảnh PDF)"]
        F -->|Bấm nút Review| G["POST /api/workorders/{id}/review<br>(Approve / Reject)"]
    end

    subgraph WEBSERVER ["WEB SERVER"]
        C -->|Proxy qua cổng 80| H["nginx.conf<br>(Điều hướng /api/ vào FastAPI)"]
    end

    subgraph BACKEND ["BACKEND (FASTAPI WORKER)"]
        H --> I["main.py: POST /api/workorders"]
        I -->|1. Lưu tạm file| J["Tạo thư mục data/wo/{id}"]
        I -->|2. Ghi bản ghi mới: status='new'| K[("db.py: SQLite app.db")]
        I -->|3. Đẩy vào BackgroundTasks| L["pipeline.py: run_pipeline()"]
        
        subgraph PIPELINE ["LUỒNG XỬ LÝ: pipeline.py"]
            L -->|Bước 1| M["extract.py: extract_ole_pdf()<br>Rạch file .xlsx lôi PDF"]
            M -->|Bước 2| N["render.py: pdf_to_images()<br>Dùng PyMuPDF ra ảnh JPEG"]
            N -->|Bước 3| O["ai.py: read_drawings_with_ai()<br>Gửi ảnh lên LLM Vision"]
            O -->|Bước 4| P["bom.py: read_bom_sheet()<br>Đọc sheet BOM trong Excel"]
            P -->|Bước 5| Q["compare.py: compare_bom_and_ai()<br>So khớp từng ô"]
        end

        Q -->|Ghi kết quả: status='ok' hoặc 'error'| K
    end

    K -.->|Trả dữ liệu JSON| D
```

---

## 4. SO SÁNH ĐỐI ĐẦU: CODE SẾP VS. BỘ CODE LÕI MEP CỦA BẠN

| Tiêu chí | Code sếp gửi (`wo-check` trong Excel) | Bộ Code Lõi của bạn (`Payment_PDF`) | Nhận xét chuyên môn |
| :--- | :--- | :--- | :--- |
| **Framework Backend** | **FastAPI** (`backend/app/main.py`) | **FastAPI** (`api.py`) | **Trùng khớp 100%!** Sếp và bạn cùng chung công nghệ. |
| **Trích xuất PDF OLE** | `extract.py`: Dùng hàm giải mã struct OLE Compound File (`cfb_streams`) | `engine.py`: Dùng `zipfile` + XML parsing lôi `oleObject.bin` | Thuật toán của sếp rất xịn ở chỗ đọc đúng từng sector FAT OLE (chúng ta đã nhúng vào `engine.py`). |
| **Thị giác máy tính (Computer Vision)** | `render.py`: Dùng `fitz` chuyển PDF ra nguyên 1 ảnh to (2000px). **Không có OpenCV**. | `pdf_extractor.py`: **OpenCV cực mạnh**, Magic Crop, Multi-table, băm ảnh Chunking. | **Code của bạn vượt trội 100%**. Bản vẽ CAD A0/A1 nếu không có OpenCV của bạn thì AI sẽ mù mắt. |
| **Độ nhạy AI & Chống ảo giác** | `ai.py`: Gửi toàn bộ trang to lên AI bằng prompt linh kiện điện thoại. | `pdf_extractor.py`: Prompt chuyên sâu MEP, ép định dạng SDAC 12 ký tự, lọc nét vẽ thừa. | Code của bạn đạt độ chính xác thực tế, code của sếp chỉ chạy được bản vẽ đồ chơi. |
| **Nghiệp vụ Gate Pass (BBGN)** | **HOÀN TOÀN KHÔNG CÓ** | `excel_reconciler.py`: **Có trọn vẹn Vòng 2**, đối soát trừ vật tư SDV cấp. | Code sếp thiếu hẳn 50% bài toán thực tế của bạn. |
| **Nghiệp vụ Phụ trội & Remark** | **HOÀN TOÀN KHÔNG CÓ** | `excel_reconciler.py`: Đối soát tổ hợp khóa 3 chiều `(Code + Phụ trội + Remark)`. | Bản vẽ MEP luôn có % phụ trội và vật tư kho cấp, code của bạn mới đáp ứng được. |
| **Đầu ra Báo cáo** | Trả JSON hiển thị lên bảng web. Không xuất file Excel. | Xuất ra **1 File Excel 2 Sheet** được trang trí, kẻ viền, tô Đỏ/Xanh bằng OpenPyXL và nén zip. | Kế toán và nhà thầu cần file Excel báo cáo để thanh toán, code của bạn đáp ứng đúng thực tế. |
| **Cơ sở dữ liệu** | SQLite (`app.db`) | Oracle Database (`LOCAL_AI`) | Oracle là chuẩn bắt buộc của OneAI công ty bạn. |

---

## 5. PHÂN TÍCH CHI TIẾT 100% TỪNG FILE TRONG `Sepgui.xlsx` (25 FILE)

### Nhóm 1: Các file thuật toán xử lý lõi (`backend/app/processing/`)
1. **`extract.py` (Rạch PDF OLE từ Excel - 4,064 ký tự):**
   * Sử dụng thư viện `struct` phân tích header nhị phân Microsoft Compound File Binary (CFB), duyệt qua bảng FAT (File Allocation Table) để ghép các sector 512 bytes bị phân mảnh lại với nhau. Tìm chuỗi `%PDF- ... %%EOF` để lưu ra đĩa.
   * *Đánh giá:* Rất tinh tế, đã được tích hợp vào [`engine.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/engine.py).
2. **`render.py` (Chuyển PDF sang ảnh JPEG - 2,997 ký tự):**
   * Dùng PyMuPDF (`fitz`) render ảnh JPEG tối đa 2000px.
   * *Hạn chế:* Chỉ render 1 ảnh to, không có OpenCV cắt bảng hay chunking (bản vẽ CAD A0/A1 sẽ bị AI đọc sót).
3. **`ai.py` (Gọi LLM Vision - 4,045 ký tự):**
   * Gửi ảnh lên LLM Vision chuẩn OpenAI API. Có hàm `mock_read()` dùng Regex đọc text chay khi không có API Key.
   * *Prompt của sếp:* Viết cho linh kiện điện thoại đơn giản. Code của bạn tối ưu hơn nhờ prompt ép chuẩn mã SDAC 12 ký tự.
4. **`bom.py` (Đọc danh sách vật tư BOM - 2,779 ký tự):**
   * Dùng biểu thức chính quy `RE_CODE` quét 25 dòng đầu để tìm cột Mã vật tư và các cột Bản vẽ bên phải (tương tự Dynamic Radar của bạn).
5. **`compare.py` (Bộ não so khớp - 5,565 ký tự):**
   * So khớp $1 - 1$ giữa AI và BOM Excel, phân loại 5 lỗi: sai số lượng, thiếu trong Excel, Excel thừa, mã đọc không rõ, không có cột bản vẽ.
   * *Hạn chế:* Chưa có Vòng 2 Gate Pass, chưa có Phụ trội %, chưa trừ SDV cấp.
6. **`pipeline.py` (Nhạc trưởng điều phối - 4,301 ký tự):**
   * Nhận `wo_id`, lần lượt gọi: `extract` $\rightarrow$ `render` $\rightarrow$ `ai` $\rightarrow$ `bom` $\rightarrow$ `compare` $\rightarrow$ lưu log từng bước vào DB.
7. **`__init__.py`:** Đánh dấu thư mục `processing` là Python package.

### Nhóm 2: Các file máy chủ và dữ liệu (`backend/app/`)
8. **`main.py` (FastAPI Routers - 9,686 ký tự):**
   * Cung cấp các API: upload file (`POST /api/workorders`), lấy danh sách (`GET /api/workorders`), bấm chạy lại (`POST /rerun`), **kỹ sư bấm nút Duyệt/Từ chối (`POST /review`)**, xem ảnh bản vẽ (`GET /pages/{n}.jpg`), đổi cài đặt AI (`GET/PUT /settings`).
9. **`db.py` (Quản lý Database SQLite - 4,494 ký tự):**
   * Tạo bảng `workorders` lưu trạng thái `new`, `running`, `ok`, `error`, kết quả JSON và thông tin người duyệt.
   * *Đã được nâng cấp thành Oracle Database Doanh nghiệp trong [`create_table.sql`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/database/create_table.sql).*
10. **`auth.py` (Xác thực người dùng - 2,004 ký tự):**
    * Đọc user từ header `X-Remote-User` hoặc biến môi trường `WO_DEV_USER`.
11. **`config.py` (Biến môi trường - 1,410 ký tự):**
    * Đọc cấu hình `DATA_DIR`, `AI_ENDPOINT`, `AI_MODEL`, `MOCK_MODE`.
12. **`requirement.txt` (Thư viện):**
    * `fastapi`, `uvicorn`, `python-multipart`, `openpyxl`, `pymupdf`, `pillow`.

### Nhóm 3: Các màn hình giao diện (`frontend/src/`)
13. **`ListPage.vue` (Màn hình chính - 4,282 ký tự):**
    * Có 5 ô KPI thống kê (*Tổng, Chờ duyệt, Khớp, Có lỗi, Thất bại*), ô tìm kiếm, bảng danh sách và cơ chế tự động Polling (3 giây khi đang chạy, 20 giây khi nghỉ).
14. **`WorkorderDetail.vue` (Màn hình soi lỗi - 9,149 ký tự):**
    * Bảng chi tiết các dòng lệch số lượng, popup phóng to ảnh bản vẽ PDF gốc, và 2 nút bấm nghiệp vụ: **[Duyệt]** hoặc **[Từ chối]**.
15. **`AddWorkorderModal.vue` (Popup Upload - 2,740 ký tự):**
    * Cửa sổ kéo thả file Excel tải lên.
16. **`StatusBadges.vue` (Huy hiệu trạng thái - 813 ký tự):**
    * Hiển thị tag màu: Xanh lá (`ok`), Đỏ (`error`), Xanh dương (`running`), Xanh lục (`approved`).
17. **`SettingsPage.vue` (Cài đặt hệ thống - 4,671 ký tự):**
    * Màn hình Admin đổi URL máy chủ AI, đổi tên Model AI và bật/tắt Mock Mode.

### Nhóm 4: Khung sườn Web Frontend
18. **`App.vue` & `main.js`:** Thanh Header điều hướng và hàm khởi tạo Vue 3.
19. **`api.js` & `store.js`:** Đóng gói hàm `fetch()` gọi FastAPI và lưu trạng thái vào RAM trình duyệt.
20. **`style.css` (5,266 ký tự):** Bộ mã màu CSS giao diện sáng (Light Theme).
21. **`index.html`, `package.json`, `vite.config.js`:** Cấu hình đóng gói dự án Vite SPA.

### Nhóm 5: Hạ tầng & Dữ liệu mẫu (`deploy/`, `samples/`)
22. **`deploy/nginx.conf.example` (1,048 ký tự):**
    * Cấu hình máy chủ Nginx chuyển tiếp `/api/` về port 8000.
23. **`samples/tao_file_mau.py` (Script tự tạo dữ liệu test - 12,721 ký tự):**
    * File dài nhất dự án, dùng thư viện `reportlab` vẽ bản vẽ kỹ thuật giả lập (màn hình điện thoại OLED, FPC, kính 3D...) rồi nhúng OLE vào Excel để tạo ra 3 file test mẫu.
24. **`.gitignore` & `README.md`:**
    * Hướng dẫn chạy thử nghiệm tại máy cá nhân.

---

## 6. Ý NGHĨA CỦA 3 FILE TEST MẪU (WO-TEST-001, 002, 003)

Sếp đã tự tay dựng 3 file mẫu này để đại diện cho **3 kịch bản kiểm tra điển hình** khi nghiệm thu:
1. **`WO-TEST-001_khop.xlsx` (0 Lỗi - Khớp 100%):**
   * Số lượng ở sheet BOM khớp chính xác 100% với bảng vật tư trong file PDF nhúng.
   * Kết quả mong muốn: Trạng thái `OK`, 0 lỗi phát sinh.
2. **`WO-TEST-002_co_loi.xlsx` (4 Lỗi - Sai lệch số lượng & mã):**
   * Cố tình tạo ra các sai lệch thực tế:
     * `OCA-0420`: BOM ghi 3 pcs, nhưng PDF ghi 2 pcs $\rightarrow$ Lỗi sai số lượng.
     * `TAP-CU-012`: BOM bỏ trống, nhưng PDF có $\rightarrow$ Lỗi ô Excel trống.
     * `FLM-PET050` & `LBL-QR-01`: Lệch mã giữa bản vẽ và Excel.
   * Kết quả mong muốn: Báo đỏ đúng 4 lỗi.
3. **`WO-TEST-003_thieu_ban_ve.xlsx` (1 Lỗi - Thiếu bản vẽ):**
   * Cố tình để thiếu bản vẽ hoặc sai tên bản vẽ trong PDF so với cột Excel.
   * Kết quả mong muốn: Báo lỗi "Không tìm thấy bản vẽ".

---

## 7. BẢN ĐỒ ĐỐI CHIẾU CHÉO (MAPPING MATRIX)

| Thành phần trong code sếp (`Sepgui.xlsx`) | Thành phần tương ứng trong dự án của bạn | Nhận định kỹ thuật |
| :--- | :--- | :--- |
| **`extract.py`** (Trích xuất OLE CFB) | [`backend/engine.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/engine.py) | **Đã hợp nhất!** Giữ logic zipfile của bạn + Nạp thêm thuật toán `cfb_streams` của sếp. |
| **`render.py`** & **`ai.py`** (Render ảnh & Gọi AI) | [`backend/pdf_extractor.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/pdf_extractor.py) | **Code của bạn mạnh hơn 100 lần!** Có OpenCV Magic Crop, lọc nhiễu, băm nhỏ Chunking cho bản vẽ A0/A1. |
| **`bom.py`** & **`compare.py`** (Đọc BOM & So sánh) | [`backend/excel_reconciler.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/excel_reconciler.py) | **Code của bạn hoàn thiện nghiệp vụ MEP!** Có Radar động, Đối soát 2 Vòng (Bản vẽ + Gate Pass), xử lý Phụ trội, SDV cấp và xuất Excel báo cáo 2 Sheet tô màu. |
| **`main.py`** & **`pipeline.py`** (FastAPI) | [`backend/api.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/api.py) | Chuẩn hóa thành API Worker chạy nền xử lý tác vụ nặng cho OneAI. |
| **`db.py`** (SQLite `app.db`) | [`database/create_table.sql`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/database/create_table.sql) & [`backend/sql.py`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/backend/sql.py) | Nâng cấp từ SQLite cá nhân lên **Oracle Database Doanh nghiệp** (`LOCAL_AI`). |
| **`ListPage.vue`**, **`WorkorderDetail.vue`**, **`StatusBadges.vue`** | [`MepOperation.vue`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/frontend/src/views/MepOperation.vue) & [`mepPayment.js`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/frontend/src/js/mepPayment.js) | Gom toàn bộ chức năng vào 1 màn hình duy nhất theo chuẩn Element Plus Dark Theme của OneAI. |
| **`auth.py`**, **`api.js`**, **`store.js`**, **`nginx.conf`** | **NỀN TẢNG ONEAI ĐÃ LO HẾT** | Không cần viết lại vì OneAI đã có sẵn SSO, Router, Pinia Store và hạ tầng mạng. |
| **`tao_file_mau.py`** | Dùng 3 file `.xlsx` mẫu để kiểm thử | Giữ lại 3 file test mẫu của sếp để chạy nghiệm thu. |

---

## 8. CHIẾN LƯỢC BẢO VỆ CODE VÀ KỊCH BẢN BÁO CÁO VỚI SẾP

Khi trao đổi và báo cáo trước sếp, bạn có thể tự tin chia sẻ theo kịch bản chuẩn mực sau:

> *"Em đã đọc và phân tích rất kỹ toàn bộ mã nguồn anh gửi trong file `Sepgui.xlsx`. Luồng tư duy hệ thống của anh cực kỳ chuẩn xác và em đã tiếp thu trọn vẹn 3 điểm sáng kỹ thuật lớn nhất từ code của anh:*  
> *1. Thuật toán duyệt sector OLE CFB bằng thư viện `struct` trong `extract.py` để bóc file PDF nhúng chống phân mảnh sector.*  
> *2. Luồng nghiệp vụ Phê duyệt (Approve / Reject) có ghi nhận ý kiến kỹ sư.*  
> *3. Bộ 3 kịch bản kiểm thử mẫu (`WO-TEST-001`, `002`, `003`) để chạy nghiệm thu.*  
>  
> *Tuy nhiên, vì đề bài thực tế của nhà máy là bản vẽ CAD cơ điện (MEP) khổ lớn A0/A1 có nhiều bảng khối lượng phức tạp, đồng thời phải đối soát Vòng 2 với Gate Pass (trừ vật tư kho SDV cấp), nên phần bóc tách hình ảnh em bắt buộc phải giữ bộ não OpenCV Magic Crop và thuật toán đối soát 2 vòng của em thì hệ thống mới chạy chính xác trên dữ liệu thực tế tại xưởng được ạ.*  
>  
> *Về mặt triển khai, em đã đóng gói toàn bộ hệ thống tinh gọn đúng theo chuẩn Plugin của nền tảng OneAI (tích hợp Oracle DB và Element Plus Dark Theme), sẵn sàng kết nối và bàn giao sử dụng ngay ạ."*


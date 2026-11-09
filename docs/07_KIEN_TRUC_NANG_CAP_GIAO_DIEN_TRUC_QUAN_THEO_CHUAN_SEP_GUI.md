# TÀI LIỆU HƯỚNG DẪN & THIẾT KẾ KIẾN TRÚC NÂNG CẤP GIAO DIỆN ONEAI THEO CHUẨN SẾP GỬI

> **Ngày hoàn thành**: 2026-11-04  
> **Hệ thống**: MEP OneAI Payment Analysis System  
> **Mục tiêu**: Chuyển đổi trải nghiệm từ "Bảng quản lý file phẳng" sang "Hệ thống Dashboard Đối Soát Doanh Nghiệp (ERP/MES) Trực Quan & Toàn Diện", kế thừa các tinh hoa từ dự án mẫu của Sếp (`wo-check`).

---

## 1. TỔNG QUAN KẾ HOẠCH NÂNG CẤP

### 1.1. So sánh Trước và Sau nâng cấp

```
TRƯỚC NÂNG CẤP:
┌────────────────────────────────────────────────────────────────────────┐
│ Bộ lọc dropdown -> Nút Reload / Insert / Save / Export / Delete        │
│ Bảng phẳng: Khi COMPLETED chỉ báo "❌ Lệch 4 lỗi" -> Bắt buộc tải       │
│ file Excel về máy, mở Microsoft Excel, tự kéo tìm dòng đỏ rất bất tiện.│
└────────────────────────────────────────────────────────────────────────┘

SAU NÂNG CẤP (THEO CHUẨN SẾP GỬI):
┌────────────────────────────────────────────────────────────────────────┐
│ 5 THẺ KPI THỐNG KÊ (Tổng | Khớp 100% | Có sai lệch | Đang chạy | Mới)  │
│ -> BẤM VÀO THẺ NÀO LÀ BẢNG TỰ LỌC THEO TRẠNG THÁI ĐÓ NGAY LẬP TỨC.     │
│                                                                        │
│ BẢNG CHÍNH:                                                            │
│ Bấm vào nhãn lỗi hoặc Bấm đúp dòng -> BẬT MODAL CHI TIẾT ĐỐI SOÁT:     │
│ ├── 1. Tóm tắt nhanh: Số lỗi, số bản vẽ, số dòng vật tư, sheet BOM     │
│ ├── 2. Badges phân loại lỗi: Lệch khối lượng, Mã mồ côi, Gate Pass     │
│ ├── 3. Tab Danh sách lỗi: Mã SDAC, Tên, SL Dự toán, SL Bản vẽ, Lệch    │
│ ├── 4. Tab Bản vẽ (Accordion): Tự bung nhóm bản vẽ bị sai sót          │
│ ├── 5. Tab Soi bản vẽ: Dải ảnh thumbnail + Zoom toàn màn hình Lightbox │
│ ├── 6. Tab Nhật ký AI: Xem console log từng bước chạy                  │
│ └── 7. Khối Phê duyệt: Nhập ghi chú, Duyệt, Từ chối, Tải Zip & RERUN   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. NGUYÊN TẮC THIẾT KẾ: BẢO TOÀN 100% LUỒNG LOGIC NGHIỆP VỤ

1. **Không đập đi xây lại**: Giữ nguyên toàn bộ logic hiện tại:
   - Thư viện kết nối Oracle DB (`get_cur()`, `insert_task()`, `update_task()`, `save_tasks()`, `delete_tasks()`).
   - Quy trình nạp file Excel và chạy nền `BackgroundTasks`.
   - Cơ chế **Smart Polling 3s** (tự kích hoạt khi có dòng `RUNNING` và tự tắt khi hoàn thành).
   - Thứ tự các nút chuẩn UX: `Reload` -> `Insert` -> `Save` -> `Export` -> `Delete`.
2. **Mở rộng an toàn (Fail-safe Fallback)**:
   - Các API chi tiết mới (`/mep_payment/detail/{keyid}`) hoạt động với cơ chế 3 lớp:
     - *Lớp 1*: Đọc file JSON cache đã phân tích.
     - *Lớp 2*: Tự động đọc và bóc tách file Excel báo cáo sẵn có trên đĩa.
     - *Lớp 3*: Tự động tạo dữ liệu dự phòng (Fallback) từ thông tin dòng để không bao giờ bị trắng trang hay crash giao diện.

---

## 3. CHI TIẾT CÁC THÀNH PHẦN MỚI ĐÃ ĐƯỢC NÂNG CẤP

### 3.1. Frontend (`operation.vue`)

#### A. Khối 5 Thẻ KPI Thống Kê Toàn Cục Cố Định (Click-to-Filter)
- **Cơ chế Cố Định Số Liệu Toàn Cục (Fixed Global Summary Stats):**
  - **Vấn đề trước đây:** Do `kpiStats` được tính bằng `computed` dựa trên mảng `tableData.value` (chỉ chứa 20 dòng của trang hiện tại), khi chuyển sang trang 2 hoặc khi bấm lọc, số trên các thẻ bị biến động liên tục (ví dụ: đang có 21 hồ sơ chờ duyệt, trang 1 hiện 20, sang trang 2 chỉ hiện 1).
  - **Giải pháp chuẩn doanh nghiệp:** Biến `kpiStats` thành `ref` lưu trữ số liệu tổng hợp toàn cục từ truy vấn `searchKpiSummary` (không bị giới hạn bởi `:STATUS` hay phân trang).
    - Ví dụ: Hệ thống có 25 hồ sơ (21 Chờ duyệt, 1 Khớp, 2 Lỗi, 1 Đang chạy) $\rightarrow$ 5 con số `25`, `1`, `2`, `1`, `21` này **luôn cố định 100%**, người dùng bấm vào thẻ nào hoặc chuyển sang trang nào thì số trên 5 thẻ vẫn giữ nguyên không đổi.
- **Phân Tách Tuyệt Đối Giữa "Khớp 100%" (`OK`) và "Có Sai Lệch" (`ERR`):**
  - Trước đây khi bấm vào "Khớp 100%" hoặc "Có sai lệch", cả 2 thẻ đều gửi `:STATUS = 'COMPLETED'` nên bảng hiển thị chung tất cả các dòng hoàn tất.
  - **Giải pháp:** Cập nhật câu truy vấn SQL trên OneAI Gateway (`mep_payment_analysis.py`) và backend API:
    - Khi lọc `OK`: Trả về đúng các dòng `STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0`.
    - Khi lọc `ERR`: Trả về đúng các dòng `STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0`.
    - Thêm cơ chế bảo vệ 2 lớp (Client-side fallback) ngay trên Vue: Đảm bảo ấn "Khớp 100%" chỉ ra đúng dòng khớp, ấn "Có sai lệch" chỉ ra đúng dòng có sai lệch.

#### B. Cột "SỐ WO", "KẾT QUẢ KIỂM TRA" & Phân Tách Sự Kiện (Không Xung Đột Inline Edit)
- **Giải quyết triệt để xung đột sự kiện (Event Collision):**
  - Trước đây, nếu gán `@row-dblclick` trên toàn bảng, khi người dùng nhấp đúp vào các ô `TÊN CÔNG VIỆC`, `PART`, `GROUP` để sửa chữ, sự kiện nổi bọt (bubbling) sẽ vô tình kích hoạt modal mở đè lên.
  - **Giải pháp chuẩn:** Gỡ bỏ hoàn toàn `@row-dblclick` trên `<el-table>`. Tách biệt 100% hai luồng:
    1. *Sửa chữ trực tiếp (Inline Editing):* Nhấp đúp vào ô `TASK_NAME`, `PART`, `GROUP`, `PIC` để bật ô nhập liệu và bấm `Save` bình thường.
    2. *Mở Modal Chi tiết:* Chỉ mở khi người dùng click chuột trái vào:
       - **Số WO (`KEYID`):** Thể hiện dạng badge `<el-tag effect="plain">` có nền xanh dịu và viền nổi bật, bấm vào là xem chi tiết.
       - **Thẻ Kết quả kiểm tra:** Bấm vào thẻ `✅ Khớp 100%` hoặc `❌ Lệch X lỗi`.
- **Dọn sạch cột "CHI TIẾT BÁO CÁO" & "TÊN CÔNG VIỆC":**
  - Mở rộng cột `TÊN CÔNG VIỆC` (`min-width="260px"`) để tên dự án không bị rớt dòng.
  - Loại bỏ hoàn toàn nút `🔍 Chi tiết` trùng lặp ở cột 12 (vì cột 10 và 11 đã đảm nhiệm mở modal).
  - Loại bỏ nút `Rerun` bừa bãi trên các dòng đã hoàn tất; nút Rerun được chuyển vào vị trí trang trọng trong Modal, ngoài bảng chỉ hiển thị khi dòng bị lỗi (`STATUS === 'CANCEL'`).
  - Cột 12 giờ chỉ gồm link tải `📥 Tải Báo Cáo (.zip)` và Tag trạng thái `Đã Duyệt` / `Từ Chối` (hoặc cụm nút Duyệt/Hủy cho kỹ sư).

#### C. Khắc Phục Lỗi STT Phân Trang (Global STT Calculation)
- **Vấn đề trước đây:** Khi `pageSize = 20` và `total = 22`:
  - Tại trang 1 bấm Insert: STT sinh ra là 21 (trùng với item đầu của trang 2).
  - Tại trang 2 (đang có 3 item) bấm Insert: STT sinh ra là 4 thay vì 24.
- **Giải pháp triệt để:** Tính toán STT toàn cục dựa trên số lớn nhất giữa `total + 1` và `currentMaxStt + 1`:
  ```javascript
  const currentMaxStt = tableData.value.reduce((max, r) => Math.max(max, Number(r.STT) || 0), 0)
  const nextStt = Math.max(Number(total.value || 0) + 1, currentMaxStt + 1)
  ```
  Đảm bảo dù đang đứng ở trang nào bấm Insert thì dòng mới luôn mang số thứ tự kế tiếp chuẩn xác 100%.

#### D. Hộp Thoại Chi Tiết Đối Soát (`<el-dialog>`)
- Độ rộng 85% màn hình, hiển thị phân cấp chuyên nghiệp:
  - **Header Card**: Thông tin mã WO, tên công việc, kỹ sư phụ trách, part, group, công nghệ AI và huy hiệu trạng thái phê duyệt.
  - **4 Mini Stats**: Đếm tổng lỗi, số bản vẽ bóc tách, tổng số dòng kiểm tra, tên sheet đối chiếu.
  - **Error Breakdown Badges**: Tự động nhóm các lỗi theo chủng loại (ví dụ: `Lệch khối lượng: 2`, `Mã mồ côi: 1`).
  - **Tabs đa năng**:
    - `Tab 1: Danh Sách Lỗi`: Bảng liệt kê chi tiết từng dòng sai sót kèm số liệu Dự toán vs Thực tế bản vẽ.
    - `Tab 2: Đối Chiếu Theo Bản Vẽ`: Accordion gập/mở, tự động mở sẵn các bản vẽ có lỗi để kỹ sư kiểm tra.
    - `Tab 3: Soi Bản Vẽ / Ảnh Trích Xuất`: Hiển thị dải ảnh thu nhỏ, nhấp vào là phóng to toàn màn hình với công cụ zoom in/out, xoay ảnh của Element Plus.
    - `Tab 4: Nhật Ký AI`: Console hiển thị toàn bộ log pipeline xử lý.
  - **Footer Actions**:
    - Ô nhập ghi chú duyệt.
    - Nút Duyệt (`APPROVED`) và Từ chối (`REJECTED`).
    - Nút Tải file báo cáo (.zip).
    - Nút **"Chạy lại AI" (Rerun)**.

#### D. Tính năng Chạy Lại AI (Rerun)
- Khi gặp trường hợp mạng chập chờn hoặc AI timeout làm dòng bị `CANCEL`, người dùng chỉ cần bấm nút `🔄 Rerun`:
  - Hệ thống gọi API `/mep_payment/rerun/{keyid}`.
  - Trạng thái tự chuyển về `RUNNING`, tiến độ reset về 5%, Smart Polling tự kích hoạt để cập nhật tiến độ mà **không cần upload lại file**.

---

### 3.2. Backend (`api.py` & `detail_builder.py`)

#### A. Module `backend/detail_builder.py`
Chịu trách nhiệm bóc tách số liệu từ file Excel kết quả 2 sheet:
- `parse_excel_report_to_detail(excel_path, keyid, session_dir)`: Quét sheet *1. Đối Soát Bản Vẽ* và *2. Đối Soát Gate Pass*, trích xuất mảng lỗi, nhóm bản vẽ, tìm kiếm ảnh bằng chứng và sinh log pipeline.
- `build_or_load_task_detail(keyid, final_report_dir, storage_dir, fallback_info)`: Cơ chế caching thông minh, lưu kết quả dưới dạng file JSON `{KEYID}_detail.json` giúp tải modal tức thì dưới 100ms.

#### B. Các API Endpoints mới trong `backend/api.py`
1. `GET /mep_payment/detail/{keyid}`: Trả về toàn bộ payload JSON chi tiết để vẽ Dialog.
2. `GET /mep_payment/image/{keyid}/{filename}`: Phục vụ ảnh bản vẽ / ảnh bằng chứng chất lượng cao cho Lightbox.
3. `POST /mep_payment/rerun/{keyid}`: Kích hoạt lại Background Task từ file Excel của phiên làm việc cũ.

---

### 3.3. Kiến trúc Dual-Theme (Dark & Light Mode) Công Nghiệp Hiện Đại (v3.0)

Nhằm tối ưu trải nghiệm người dùng theo tiêu chuẩn UI/UX Pro Max:
1. **Khả năng tự động thích ứng chế độ Sáng / Tối (Auto Theme Switch):**
   - Tự động lắng nghe thay đổi từ hệ điều hành máy tính thông qua `window.matchMedia('(prefers-color-scheme: dark)')`.
   - Tự động đồng bộ với thanh chuyển Theme của OneAI Portal (lớp `html.dark` hoặc `body[theme="dark"]`).
   - Kỹ sư chuyển máy tính từ Dark sang Light (hoặc ngược lại) thì toàn bộ giao diện bảng quản trị và modal lập tức hoán đổi màu sắc tương thích mà **không cần bấm F5**.
2. **Khắc phục lỗi Scoped CSS `:root` làm mất viền khung thẻ KPI và viền card modal:**
   - Trong Vue 3, selector `:root` khi đặt trong thẻ `<style scoped>` sẽ bị trình biên dịch chuyển thành `:root[data-v-xxxx]`. Selector này không bao giờ khớp trên trình duyệt, dẫn đến việc các biến CSS màu viền bị rỗng $\rightarrow$ làm mất toàn bộ viền bao quanh các thẻ KPI và modal.
   - **Giải pháp triệt để:** Di chuyển toàn bộ khai báo biến theme từ `:root` sang class gốc `.mep-container` và `.mep-theme-light`, đồng thời thêm cơ chế fallback màu tĩnh (`border: 1px solid #334155; border: 1px solid var(--mep-border);`). Đảm bảo thẻ KPI, modal thống kê và các đường chia bản vẽ luôn có viền rõ ràng, sắc nét.
3. **Hệ thống nhãn màu sắc động theo mức độ cảnh báo (Dynamic Tag Semantics):**
   - **Lệch khối lượng:** Tag đỏ đậm (`danger`) kèm icon mũi tên xuống/lên.
   - **Lệch tỷ lệ phụ trội:** Tag vàng cam (`warning`) kèm icon `%` (ví dụ `Lệch PT (30% vs 20%)`).
   - **Lệch ghi chú / điều kiện cấp:** Tag xanh dương (`info`) kèm icon tag (ví dụ `Lệch RM (SDV vs Trống)`).
   - **Mã mồ côi:** Tag đỏ viền trơn (`plain danger`) kèm icon cảnh báo tròn.

---

## 4. HƯỚNG DẪN KIỂM THỬ TRÊN MÔI TRƯỜNG THỰC TẾ

1. **Khởi động Backend FastAPI**:
   ```powershell
   cd d:\Project\Payment_PDF\MEP_OneAI_System\backend
   uvicorn api:app --port 8000 --reload
   ```
2. **Mở giao diện OneAI**:
   - Truy cập màn hình đối soát MEP.
   - Nhìn thấy ngay khối **5 thẻ KPI đầu trang** hiển thị tổng số hồ sơ. Bấm thử vào thẻ "Khớp 100%" hoặc "Có sai lệch" để kiểm tra lọc nhanh.
   - Bấm vào mã **Số WO** hoặc thẻ **Kết quả kiểm tra** trên một dòng đã hoàn tất: Modal đối chiếu bung lên với đầy đủ 4 tab, bảng lỗi, accordion bản vẽ và ảnh xem trước.
   - Thử bấm đúp chuột vào ô Tên công việc, Part, Group để kiểm tra chỉnh sửa inline: Modal không bị nhảy đè lên, tính năng sửa độc lập 100%.
   - Bấm thử nút `🔄 Chạy lại AI` trên một dòng bị lỗi để kiểm tra quy trình chạy lại tự động.

---

## 5. DANH MỤC CÁC FILE CẬP NHẬT HOÀN THIỆN HỆ THỐNG

Để nâng cấp toàn bộ hệ thống lên chuẩn UX/UI trực quan như hệ thống của Sếp gửi và giải quyết dứt điểm vấn đề KPI cố định:

1. **`MEP_OneAI_System/oneai_integration/frontend/operation/tab/operation.vue`** *(Frontend Vue 3)*:
   - 5 Thẻ KPI hiển thị số liệu toàn cục **CỐ ĐỊNH** (`kpiStats.value`), không bị co giãn khi chuyển trang hay khi click lọc.
   - Phân tách độc lập hoàn toàn giữa bộ lọc `Khớp 100%` (`OK`) và `Có sai lệch` (`ERR`).
   - Sửa lỗi STT phân trang bằng công thức `nextStt`.
   - Gỡ bỏ `@row-dblclick` để bảo toàn tính năng sửa chữ inline cho Task Name, Part, Group.
   - Thêm Modal Dialog 4 Tab (Bảng lỗi, Bản vẽ, Soi ảnh, Nhật ký AI, Duyệt & Rerun).
2. **`MEP_OneAI_System/oneai_integration/backend/menu_operation/mep_payment/mep_payment_analysis.py`** *(OneAI Gateway SQL)*:
   - Thêm truy vấn `searchKpiSummary`: Đếm 5 chỉ số toàn cục (Total, OK, ERR, Running, Waiting) trong 1 lần gọi duy nhất.
   - Nâng cấp câu query `searchTotalRow` và `getdata_page`: Hỗ trợ tham số `:STATUS = 'OK'` (`ERROR_COUNT = 0`) và `:STATUS = 'ERR'` (`ERROR_COUNT > 0`).
3. **`MEP_OneAI_System/oneai_integration/frontend/operation/js/mepPayment.js`** *(Frontend API Bridge)*:
   - Thêm hàm `get_kpi_summary(paymentMonth, keyword)`.
4. **`MEP_OneAI_System/backend/api.py` & `backend/sql.py`** *(FastAPI Worker & Local Database)*:
   - Bổ sung 3 API endpoints (`/mep_payment/detail/{keyid}`, `/mep_payment/image/{keyid}/{filename}`, `/mep_payment/rerun/{keyid}`).
   - Bổ sung endpoint dự phòng `GET /mep_payment/kpi_summary` đảm bảo hệ thống luôn có số liệu KPI ngay cả khi Gateway chưa cập nhật.
5. **`MEP_OneAI_System/backend/detail_builder.py`** *(Tạo mới)*:
   - Module bóc tách báo cáo Excel 2 sheet ra JSON 4 tab và cung cấp cơ chế 3-tier fallback an toàn.

> 🛡️ **Bảo toàn 100%:** Toàn bộ các file thuật toán AI lõi (`engine.py`, `excel_reconciler.py`, `pdf_extractor.py`, `config.py`, `utils.py`) đều được giữ nguyên vẹn, không cần thay đổi bất kỳ dòng code nào!


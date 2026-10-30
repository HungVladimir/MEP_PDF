# HƯỚNG DẪN TRIỂN KHAI TOÀN DIỆN HỆ THỐNG MEP ONEAI
## (DEPLOYMENT GUIDE FROM ZERO TO PRODUCTION)

> **Mục tiêu:** Hướng dẫn chi tiết từng thao tác để đưa hệ thống Bóc tách & Đối soát MEP AI lên chạy thực tế trên nền tảng OneAI của công ty.

---

## 1. TỔNG QUAN KIẾN TRÚC TRIỂN KHAI

Hệ thống gồm 3 tầng kết nối:

```
┌─────────────────────────────────┐
│  ONEAI PORTAL (VUE.JS 3)        │ <--- Giao diện Dark Theme, Table 10 cột, nút Upload & Review
└──────────────┬──────────────────┘
               │ (1) Polling 10s: GET /crud/ui
               ▼
┌─────────────────────────────────┐
│  ORACLE DATABASE (LOCAL_AI)     │ <--- Sổ cái lưu trạng thái, lỗi, link báo cáo
└──────────────▲──────────────────┘
               │ (2) Cập nhật trạng thái: WAITING -> RUNNING -> COMPLETED
┌──────────────┴──────────────────┐
│  FASTAPI WORKER (PORT 8386)     │ <--- Service AI xử lý ngầm (OpenCV + NextAI-SDV + Pandas)
└─────────────────────────────────┘
```

---

## 2. BƯỚC 1: KHỞI TẠO ORACLE DATABASE (DBEAVER)

1. Mở **DBeaver** trên máy tính công ty.
2. Kết nối tới Database Oracle (Schema: `LOCAL_AI`).
3. Mở file `database/create_table.sql` trong project này.
4. Nhấn `Ctrl + A` chọn toàn bộ nội dung $\rightarrow$ Nhấn `Alt + X` (hoặc `Ctrl + Enter`) để thực thi.
5. Kiểm tra kết quả:
   - Bảng `LOCAL_AI.MEP_PAYMENT_ANALYSIS` được tạo thành công.
   - Chạy lệnh kiểm tra:
     ```sql
     SELECT * FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS;
     ```
   - Xác nhận có 3 dòng dữ liệu mẫu đã hiển thị.

---

## 3. BƯỚC 2: CÀI ĐẶT VÀ KHỞI ĐỘNG FASTAPI WORKER

Service này chịu trách nhiệm gánh toàn bộ tải xử lý AI, chạy ngầm độc lập tại cổng `8386`.

### 2.1. Cài đặt thư viện:
Mở terminal tại thư mục `backend/`:
```bash
cd d:\Project\Payment_PDF\MEP_OneAI_System\backend
pip install -r requirements.txt
```

### 2.2. Cấu hình thông số DB trong file `sql.py`:
Mở file `backend/sql.py`, kiểm tra và điền thông số Oracle của công ty:
```python
DB_USER     = "LOCAL_AI"
DB_PASSWORD = "mat_khau_cua_ban"
DB_HOST     = "107.126.xx.xx"
DB_PORT     = 1521
DB_SERVICE  = "MBAYMS"
```

### 2.3. Khởi động Worker:
```bash
python api.py
```
Khi terminal hiện:
```
🚀 Khởi động MEP Payment AI Worker tại cổng 8386...
INFO: Uvicorn running on http://0.0.0.0:8386
```
$\rightarrow$ Backend Worker đã sẵn sàng nhận lệnh!

---

## 4. BƯỚC 3: TÍCH HỢP VÀO NỀN TẢNG ONEAI PORTAL

### 3.1. Phía Backend OneAI:
- Copy file `oneai_integration/backend/mep_payment_analysis.py` vào thư mục backend của OneAI (nơi chứa các file cấu hình `QuerySettings` như `cdm_analysis.py`).

### 3.2. Phía Frontend OneAI:
1. Copy file `oneai_integration/frontend/src/js/mepPayment.js` vào thư mục `src/js/` của Frontend OneAI.
2. Copy file `oneai_integration/frontend/src/views/MepOperation.vue` vào thư mục `src/views/` (hoặc thư mục chứa các màn hình nghiệp vụ).
3. Khai báo Route / Menu:
   - Trong file menu của OneAI (thường là `router.js` hoặc cấu hình Menu Database), thêm đường dẫn tới component `MepOperation.vue`:
     ```javascript
     {
       path: '/mep-payment',
       name: 'MEP Payment Analysis',
       component: () => import('@/views/MepOperation.vue'),
       meta: { title: 'Đối Soát Nghiệm Thu MEP' }
     }
     ```

---

## 5. BƯỚC 4: KIỂM THỬ TOÀN DIỆN (END-TO-END VERIFICATION)

1. Mở trình duyệt truy cập vào giao diện OneAI: `http://localhost:8080/#/mep-payment`.
2. Kiểm tra giao diện:
   - Thanh Toolbar: Bộ lọc Trạng thái, Tháng thanh toán, Tìm kiếm số WO.
   - Nút `Reload (10s)` đếm ngược và tự động làm mới.
   - Bảng dữ liệu đúng 10 cột chuẩn.
3. Thử nghiệm Upload:
   - Tại dòng `WOR2512230006V`, bấm nút `[+ Upload File]`.
   - Chọn 1 file Excel thanh toán thực tế (hoặc file mẫu có nhúng PDF bản vẽ & BBGN).
   - Nút bấm đổi sang `Đang chạy...`, trạng thái nhảy sang `Đang Xử Lý` màu vàng.
4. Kiểm tra kết quả AI:
   - Sau khoảng 33 giây, AI hoàn thành:
     - Dòng đổi sang màu xanh lá `Hoàn Tất`.
     - Cột kết quả hiện: `✅ Khớp 100% (0 lỗi)` hoặc `❌ Lệch X lỗi`.
     - Cột chi tiết xuất hiện link: `📥 Tải Báo Cáo 2 Sheet`.
5. Tải báo cáo và duyệt:
   - Bấm vào link để tải file `.xlsx` về máy kiểm tra tô màu Đỏ/Xanh.
   - Kỹ sư bấm nút `[Duyệt]` $\rightarrow$ Nhập ghi chú $\rightarrow$ Lưu trạng thái `Đã Duyệt` vào Oracle DB.


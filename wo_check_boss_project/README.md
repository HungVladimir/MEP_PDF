# Kiểm tra vật tư Workorder

Hệ thống này so sánh bảng vật tư trong PDF nhúng ở file Excel workorder với sheet danh sách vật tư của chính file đó.

- Người dùng upload file Excel.
- Server tách PDF, cho AI vision đọc bảng vật tư, so sánh và báo số lỗi.
- Người duyệt xem kết quả rồi bấm Duyệt hoặc Từ chối.

```
wo-check/
├── backend/            FastAPI + SQLite (Python 3.9+)
│   ├── app/
│   │   ├── main.py         API
│   │   ├── auth.py         lấy user đã đăng nhập (sửa cho khớp hệ thống của bạn)
│   │   ├── db.py           SQLite
│   │   ├── config.py       biến môi trường
│   │   └── processing/     tách PDF, render, đọc BOM, gọi AI, so sánh
│   └── requirements.txt
├── frontend/           Vue 3 + Vite
│   └── src/ (App.vue, pages/, components/, api.js, store.js)
├── samples/            3 file Excel mẫu + script tạo mẫu
└── deploy/nginx.conf.example
```

## Chạy thử trên máy dev

**Backend**

```bash
cd backend
pip install -r requirements.txt
WO_DEV_USER="nv001|Người dùng thử|reviewer" uvicorn app.main:app --port 8000 --reload
```

Biến `WO_DEV_USER` giả lập user đã đăng nhập. Khi chạy thật thì bỏ biến này.

**Frontend** (terminal khác)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 , /api tự chuyển sang :8000
```

Mặc định hệ thống bật **chế độ thử** (không gọi AI). Upload 3 file trong `samples/` sẽ cho kết quả như sau:

| File | Số lỗi |
|---|---|
| WO-TEST-001_khop.xlsx | 0 |
| WO-TEST-002_co-loi.xlsx | 4 |
| WO-TEST-003_thieu-ban-ve.xlsx | 1 |

## Chạy thật

1. Build frontend:
   ```bash
   cd frontend
   npm run build
   ```
   Kết quả nằm trong `frontend/dist`. Có thể để nginx phục vụ thư mục này. Hoặc nếu `dist` nằm cạnh `backend`, FastAPI tự phục vụ luôn.
2. Chạy backend:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```
   Chỉ dùng **1 worker uvicorn**. Lý do: việc xử lý chạy trong thread của chính process. Muốn xử lý nhiều workorder song song thì tăng `WO_WORKERS`.
3. Cấu hình nginx theo `deploy/nginx.conf.example`. Nhớ đặt `client_max_body_size` đủ lớn cho file Excel.
4. Vào **Cài đặt**:
   - bỏ chọn "Chế độ thử";
   - nhập Base URL của vLLM và tên model **vision** (ví dụ Qwen2.5-VL). Backend là bên gọi vLLM, nên không cần bật CORS cho vLLM.

### Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `WO_DATA_DIR` | `backend/data` | Chứa DB SQLite, file Excel đã upload và ảnh trang |
| `WO_WORKERS` | 2 | Số workorder xử lý cùng lúc |
| `WO_MAX_UPLOAD_MB` | 100 | Dung lượng file tối đa |
| `WO_DEV_USER` | (trống) | User giả lập khi chạy dev |
| `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY`, `WO_MOCK` | | Giá trị mặc định ban đầu. Sau khi lưu trên giao diện thì giá trị trong DB được dùng |

### Thư viện đọc PDF

Dùng **PyMuPDF** (`pip install pymupdf`, chỉ cần 1 file wheel, dễ cài offline). Nếu không cài được PyMuPDF, backend tự chuyển sang `pdftoppm` / `pdftotext` (gói poppler-utils).

## Nối với hệ thống đăng nhập

Hệ thống giả định người dùng **đã đăng nhập**. Hàm `backend/app/auth.py::get_current_user` lấy user theo thứ tự:

1. `request.state.user`, do middleware xác thực có sẵn của bạn gán;
2. các header `X-Remote-User`, `X-Remote-Name` (họ tên URL-encode), `X-Remote-Roles` do nginx/SSO gắn;
3. biến `WO_DEV_USER` khi chạy dev.

User có role `reviewer` hoặc `admin` được duyệt và sửa cài đặt. Người tạo hoặc người duyệt được xoá workorder.

Nếu hệ thống của bạn đã có dependency `get_current_user` riêng, chỉ cần thay hàm trong `auth.py`, miễn là trả về object `User(username, name, roles)`.

## API chính

| Method | Đường dẫn | |
|---|---|---|
| GET | `/api/me` | user hiện tại |
| GET | `/api/workorders?status=&q=` | danh sách + thống kê |
| POST | `/api/workorders` | multipart: `wo`, `description`, `file` (xlsx), `pdf` (tuỳ chọn) |
| GET | `/api/workorders/{id}` | chi tiết + kết quả |
| POST | `/api/workorders/{id}/rerun` | chạy lại |
| POST | `/api/workorders/{id}/file` | upload lại Excel |
| POST | `/api/workorders/{id}/review` | `{"decision":"approved"/"rejected","note":""}` |
| DELETE | `/api/workorders/{id}` | xoá |
| GET | `/api/workorders/{id}/pages/{n}.jpg` | ảnh trang PDF |
| GET | `/api/export` | báo cáo Excel |
| GET/PUT | `/api/settings`, POST `/api/settings/test-ai` | cài đặt |

Tài liệu API tự sinh có ở `/api/docs`.
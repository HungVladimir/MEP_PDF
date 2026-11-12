# ====================================================================
# DOCKERFILE - MEP ONEAI SYSTEM BACKEND WORKER
# Khuyên dùng Base Image Python 3.11 Slim (Nhẹ, ổn định, bảo mật cao)
# ====================================================================

FROM python:3.11-slim

# Thiết lập biến môi trường Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Ho_Chi_Minh

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các thư viện hệ điều hành cần thiết cho OpenCV, PyMuPDF và Oracle Client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python Dependencies trước (tận dụng Docker Layer Cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn Backend vào container
COPY . /app/

# Tạo các thư mục lưu trữ dữ liệu tạm nếu chưa có
RUN mkdir -p /app/sessions /app/final_reports /app/output /app/input_pdf

# Khai báo cổng API FastAPI
EXPOSE 8000

# Kiểm tra trạng thái hoạt động (Healthcheck)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Lệnh khởi chạy Server FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

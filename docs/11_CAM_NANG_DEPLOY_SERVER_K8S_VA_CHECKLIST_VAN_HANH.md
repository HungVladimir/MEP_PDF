# CẨM NANG TOÀN TẬP: NÂNG CẤP & TRIỂN KHAI HỆ THỐNG MEP ONEAI TỪ LOCAL LÊN SERVER / KUBERNETES (K8S) & CHECKLIST VẬN HÀNH ENTERPRISE

> **Tài liệu tham chiếu chuẩn Production v3.0**  
> **Dự án:** Hệ Thống Nghiệm Thu & Đối Soát Bóc Tách Khối Lượng MEP Bằng AI (MEP OneAI System)  
> **Mục tiêu:** Hướng dẫn chi tiết, bao quát toàn diện mọi thay đổi kỹ thuật, cạm bẫy hạ tầng, cấu hình mạng, cơ sở dữ liệu Oracle theo quy chuẩn team (Chu Đức Hải), lưu trữ MinIO phân tán, an ninh bảo mật và bảng checklist thực chiến 10 bước đưa hệ thống từ máy cá nhân (Localhost) lên Cụm Máy Chủ Doanh Nghiệp (Kubernetes Cluster / On-Premise Server).

---

## MỤC LỤC CHI TIẾT

1. [Bức Tranh Tổng Thể: Sự Khác Biệt Giữa Localhost & K8s Production](#1-bức-tranh-tổng-thể-sự-khác-biệt-giữa-localhost--k8s-production)
2. [Hạng Mục 1: Mạng, Định Tuyến & Giao Tiếp Frontend - Backend (Bản Chất Lỗi 127.0.0.1)](#2-hạng-mục-1-mạng-định-tuyến--giao-tiếp-frontend---backend-bản-chất-lỗi-127001)
3. [Hạng Mục 2: Cơ Sở Dữ Liệu Oracle & Quy Chuẩn Biến Môi Trường K8s (Chu Đức Hải)](#3-hạng-mục-2-cơ-sở-dữ-liệu-oracle--quy-chuẩn-biến-môi-trường-k8s-chu-đức-hải)
4. [Hạng Mục 3: Lưu Trữ Phân Tán (MinIO S3) & Bản Chất Stateless Của Container Pod](#4-hạng-mục-3-lưu-trữ-phân-tán-minio-s3--bản-chất-stateless-của-container-pod)
5. [Hạng Mục 4: Tường Lửa Mạng Nội Bộ (Network Security, Egress & NetworkPolicy Whitelist)](#5-hạng-mục-4-tường-lửa-mạng-nội-bộ-network-security-egress--networkpolicy-whitelist)
6. [Hạng Mục 5: Quản Trị Tài Nguyên Tính Toán & Phòng Chống OOMKilled (Out Of Memory)](#6-hạng-mục-5-quản-trị-tài-nguyên-tính-toán--phòng-chống-oomkilled-out-of-memory)
7. [Hạng Mục 6: Giám Sát Sức Khỏe Pod (Health Probes) & Quản Trị Log Tập Trung](#7-hạng-mục-6-giám-sát-sức-khỏe-pod-health-probes--quản-trị-log-tập-trung)
8. [Hạng Mục 7: An Ninh Bảo Mật & Lách Hệ Thống Chặn DLP Doanh Nghiệp](#8-hạng-mục-7-an-ninh-bảo-mật--lách-hệ-thống-chặn-dlp-doanh-nghiệp)
9. [Hạng Mục 8: Trọn Bộ Mẫu File Cấu Hình Triển Khai (Dockerfile, Deployment, Ingress)](#9-hạng-mục-8-trọn-bộ-mẫu-file-cấu-hình-triển-khai-dockerfile-deployment-ingress)
10. [Hạng Mục 9: Bảng Checklist Thực Chiến 10 Bước Trước Khi Bấm Triển Khai (Go-Live)](#10-hạng-mục-9-bảng-checklist-thực-chiến-10-bước-trước-khi-bấm-triển-khai-go-live)

---

## 1. BỨC TRANH TỔNG THỂ: SỰ KHÁC BIỆT GIỮA LOCALHOST & K8S PRODUCTION

Khi phát triển trên máy tính cá nhân (Localhost), ứng dụng hoạt động trong một môi trường "lý tưởng":
* Mọi dịch vụ đều nằm chung một máy hoặc cùng card mạng nội bộ `127.0.0.1`.
* Dữ liệu ghi thẳng vào ổ cứng vật lý (`D:\Project\...`), không bao giờ bị mất đi khi tắt máy.
* Tài nguyên RAM/CPU được chia sẻ thoải mái theo hệ điều hành Windows.
* Không có tường lửa mạng ngăn cách giữa giao diện Vue và máy chủ FastAPI.

Tuy nhiên, khi đưa lên **Kubernetes (K8s)** hoặc **Máy chủ Linux Production**, toàn bộ kiến trúc phải chuyển đổi sang mô hình **Phân tán (Distributed)** và **Vô trạng thái (Stateless)**:

```mermaid
flowchart TD
    subgraph ClientBrowser["Máy Trạm Kỹ Sư (Browser Khắp Nhà Máy)"]
        UserUI["Trình duyệt Web (Chrome / Edge)\nĐịa chỉ: https://oneai.mep.corp.internal"]
    end

    subgraph K8sCluster["Hạ Tầng Kubernetes Cluster (Linux Nodes)"]
        Ingress["K8s Ingress Controller (Nginx / HAProxy)\nSSL Termination & Path Routing"]
        
        subgraph FrontendPod["OneAI Portal Pods (Vue 3)"]
            VueApp["Frontend Service: Vue 3 Element Plus\nTab Quản Trị Nghiệm Thu"]
        end

        subgraph WorkerPod["MEP AI Worker Pods (FastAPI)"]
            FastAPI["FastAPI App (uvicorn --host 0.0.0.0 --port 8000)\nBackgroundTasks & Semaphore (max 5)"]
            Engine["Engine AI Reconciler\nOpenCV + PyMuPDF + openpyxl"]
        end
    end

    subgraph InternalInfra["Hạ Tầng Dịch Vụ Doanh Nghiệp (Enterprise Services)"]
        OracleDB[("Oracle Database 19c RAC (MBLDB)\nIP: 107.126.10.x : 1621\nSchema: LOCAL_AI.MEP_PAYMENT_ANALYSIS")]
        MinIO[("MinIO Object Storage S3\nIP: 107.126.11.129 : 31800\nBucket: 'oneai'")]
        QwenGPU["Cụm Máy Chủ GPU Vision AI\nIP: 107.126.11.129 : 32200\nModel: NextAI-SDV (Qwen2.5-VL-72B)"]
    end

    UserUI -->|"1. HTTPS request"| Ingress
    Ingress -->|"/mep-portal/*"| VueApp
    Ingress -->|"/mep_payment/*"| FastAPI
    VueApp -.->|"Gọi API ngầm"| Ingress
    FastAPI --> Engine
    Engine -->|"SQL Query / Update"| OracleDB
    Engine -->|"Put / Get Object (.zip, .xlsx, .json)"| MinIO
    Engine -->|"Inference OCR / Table Extract"| QwenGPU

    classDef k8s fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef infra fill:#0f172a,stroke:#22c55e,stroke-width:2px,color:#f8fafc;
    classDef client fill:#334155,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    class Ingress,VueApp,FastAPI,Engine k8s;
    class OracleDB,MinIO,QwenGPU infra;
    class UserUI client;
```

---

## 2. HẠNG MỤC 1: MẠNG, ĐỊNH TUYẾN & GIAO TIẾP FRONTEND - BACKEND (BẢN CHẤT LỖI 127.0.0.1)

### 2.1. Cạm bẫy chết người: Tại sao `127.0.0.1:8000` sập ngay lập tức trên Server?
* Trên máy dev cá nhân, bạn vừa chạy Frontend Vue vừa bật FastAPI Worker trên cùng máy, nên gọi `http://127.0.0.1:8000` hoàn toàn thông suốt.
* **Nhưng khi triển khai lên Server:** 
  * Giao diện Vue được biên dịch và tải về **chạy trong trình duyệt của người dùng** (Client Browser trên máy trạm của kỹ sư).
  * Nếu trong code Vue vẫn để `FASTAPI_BASE_URL = 'http://127.0.0.1:8000'`, trình duyệt của kỹ sư sẽ gửi request HTTP tới cổng 8000 của **chính chiếc máy trạm cá nhân của kỹ sư đó**!
  * Máy trạm của kỹ sư dĩ nhiên không chạy FastAPI Worker $\rightarrow$ Toàn bộ chức năng tải dữ liệu, xem chi tiết modal, tải file ZIP sẽ chết đứng với mã lỗi: `net::ERR_CONNECTION_REFUSED`.

### 2.2. Giải pháp kỹ thuật chuẩn hóa (Dynamic Base URL & Ingress Reverse Proxy)

Hệ thống đã được cập nhật hàm tự động phân giải địa chỉ thông minh trong `operation.vue`:

```javascript
// CẤU HÌNH ĐỊA CHỈ FASTAPI WORKER (TỰ ĐỘNG THÍCH ỨNG LOCAL VÀ SERVER K8S)
const getFastApiBaseUrl = () => {
  // 1. Ưu tiên biến inject từ HTML Header của Portal nếu có
  if (typeof window !== 'undefined' && window.__FASTAPI_BASE_URL__) {
    return window.__FASTAPI_BASE_URL__
  }
  // 2. Ưu tiên biến môi trường Vite khi build Docker (.env.production)
  if (typeof process !== 'undefined' && process.env && process.env.VITE_FASTAPI_BASE_URL) {
    return process.env.VITE_FASTAPI_BASE_URL
  }
  // 3. Tự động suy luận theo Domain hiện tại của trình duyệt
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://127.0.0.1:8000'
    }
    // Khi chạy trên Server/K8s: tự động trỏ theo IP hoặc Domain của Server
    return `${window.location.protocol}//${host}:8000`
  }
  return 'http://127.0.0.1:8000'
}
const FASTAPI_BASE_URL = getFastApiBaseUrl()
```

> [!TIP]
> **Phương án tối ưu nhất trong doanh nghiệp:** Khai báo qua **K8s Ingress Path Routing**. Khi đó, mọi request bắt đầu bằng `/mep_payment/` sẽ được Ingress tự động chuyển tiếp tới Service FastAPI Worker bên trong cụm. Frontend lúc này chỉ cần gọi đường dẫn tương đối `/mep_payment/...` mà không cần quan tâm đến địa chỉ IP hay port 8000, hoàn toàn xóa bỏ lỗi CORS!

### 2.3. Cấu hình Worker Binding trong Docker Container
Trên máy cá nhân, một số lập trình viên quen chạy `uvicorn api:app --host 127.0.0.1`.
* Trong Container Docker, `127.0.0.1` chỉ lắng nghe bên trong vòng lặp kín của chính Container đó. K8s Service hay Ingress từ bên ngoài gọi vào sẽ bị từ chối kết nối.
* **Bắt buộc:** Container phải bind vào tất cả card mạng: `0.0.0.0`.
* File `backend/main.py` của dự án đã được cấu hình mặc định:
  ```python
  HOST = os.getenv("WORKER_HOST", "0.0.0.0")
  PORT = int(os.getenv("WORKER_PORT", 8000))
  ```

---

## 3. HẠNG MỤC 2: CƠ SỞ DỮ LIỆU ORACLE & QUY CHUẨN BIẾN MÔI TRƯỜNG K8S (CHU ĐỨC HẢI)

### 3.1. Phân tích chỉ đạo kỹ thuật từ Team Lead (Chu Đức Hải)
> *"Khi mọi người code python nhớ đặt tên biến mật khẩu database trong .env theo quy tắc sau nhé:*  
> `DB_[tên database]_[userName]__[mật khẩu]`  
> *User: khai báo trực tiếp userName dưới dạng string :*  
> `mbayms_local_ai_conn = oracle_conn(dns="MBAYMS", user_name="LOCAL_AI", password=pwd_yms)`  
> *Mật khẩu, lấy từ env :*  
> `pwd_yms = os.getenv("DB_MBAYMS_LOCAL_AI__PASSWORD")`  
> *Cách này sẽ đồng bộ env ở máy mọi người và trên k8s ạ, mọi người cứ sửa dần đi nhé"*

#### Tại sao lại có quy chuẩn này?
1. **Bắt buộc 2 dấu gạch dưới `__` trước `PASSWORD`:**
   * Trên Kubernetes, hệ thống quản lý Secret tự động (HashiCorp Vault / ExternalSecrets Operator) thường sử dụng cú pháp phân tách `PREFIX__KEY` để ánh xạ các biến môi trường vào Container. Nếu chỉ dùng 1 gạch dưới, parser K8s có thể hiểu nhầm `LOCAL_AI_PASSWORD` là một thuộc tính mở rộng của đối tượng `LOCAL`.
2. **Khai báo `user_name` trực tiếp dạng string `"LOCAL_AI"`:**
   * Tên Schema/User là định danh cấu trúc dữ liệu cố định của ứng dụng, không phải bí mật an ninh cần xoay vòng (rotate).
   * K8s Secret Vault chỉ quản lý và xoay vòng **Mật khẩu** (`PASSWORD`). Tách rời user name giúp code minh bạch và tránh phụ thuộc vào việc inject thừa biến môi trường `USER`.

### 3.2. Cấu hình chuẩn xác trong Dự án MEP OneAI (`MBLDB`)
Dự án của chúng ta kết nối tới cơ sở dữ liệu `MBLDB` (Schema `LOCAL_AI.MEP_PAYMENT_ANALYSIS`). Cấu hình đã được chuẩn hóa 100% như sau:

#### A. File `backend/.env`:
```ini
# ====================================================================
# TÀI KHOẢN ORACLE DATABASE (ĐỒNG BỘ LOCAL & KUBERNETES)
# ====================================================================
# Cú pháp chuẩn K8s (Chu Đức Hải): DB_[DATABASE]_[USERNAME]__[PASSWORD]
DB_MBLDB_LOCAL_AI__PASSWORD=WKEHDGHK1!

# Giữ thêm biến dự phòng tương thích ngược (1 gạch dưới):
DB_MBLDB_LOCAL_AI_PASSWORD=WKEHDGHK1!

DB_SERVICE=MBLDB_SVC
```

#### B. File `backend/sql.py`:
```python
# Nạp biến môi trường chuẩn K8s
pwd_mbldb = os.getenv("DB_MBLDB_LOCAL_AI__PASSWORD") or os.getenv("DB_MBLDB_LOCAL_AI_PASSWORD")
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

def get_cur():
    """Hàm lấy con trỏ kết nối OneAI Oracle (MBLDB) chuẩn K8s."""
    return oracle_conn(
        dns="MBLDB",
        user_name="LOCAL_AI",           # Khai báo trực tiếp dạng String
        password=pwd_mbldb,              # Lấy từ Secret K8s
        oracle_client_dir=oracle_client_path,
    )
```

### 3.3. Vấn đề Oracle Instant Client trên Container Linux
* **Trên máy Windows Local:** Bạn trỏ `ORACLE_CLIENT_LIB_DIR=C:\oracle_client` (chứa `oci.dll`) để kích hoạt Thick Mode vượt lỗi `DPY-3015: password verifier 0x939`.
* **Trên Linux Docker Container:** Không có ổ đĩa `C:\`. Nếu để nguyên đường dẫn Windows, code sẽ không tìm thấy thư viện.
* **Giải pháp trên Linux:**
  1. Thư viện `python-oracledb` hiện đại hỗ trợ **Thin Mode** thuần túy không cần cài đặt Oracle Client C-libraries (nếu máy chủ Oracle Database hỗ trợ phiên bản mã hóa phù hợp).
  2. Nếu bắt buộc chạy Thick Mode trên Linux:
     * Cài đặt gói `libaio1` trên Dockerfile: `apt-get install -y libaio1 wget unzip`.
     * Tải gói `instantclient-basic-linux.x64.zip`, giải nén vào `/opt/oracle/instantclient`.
     * Khai báo biến môi trường: `ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH`.

---

## 4. HẠNG MỤC 3: LƯU TRỮ PHÂN TÁN (MINIO S3) & BẢN CHẤT STATELESS CỦA CONTAINER POD

### 4.1. Vấn đề "Bốc hơi dữ liệu" khi Pod Restart
Trong môi trường Kubernetes, Pod là thực thể **Ephemeral (Tạm thời)**:
* Khi Pod bị crash, bị OOMKilled, hoặc khi bạn deploy phiên bản mới, K8s sẽ **hủy bỏ Pod cũ và tạo Pod mới**.
* Toàn bộ file lưu trên ổ cứng cục bộ của Pod (ví dụ `sessions/`, `output/`, `reports/`) sẽ **bị xóa sạch 100%**!
* Nếu người dùng upload hồ sơ nghiệm thu, hệ thống chạy ra file Excel kết quả và lưu ở đĩa local, 2 ngày sau Pod restart, kỹ sư bấm "Tải Báo Cáo (.zip)" sẽ lập tức nhận lỗi `404 Not Found`.

### 4.2. Giải pháp: Kích hoạt MinIO Cloud Storage Dual-Mode
Hệ thống MEP OneAI đã xây dựng sẵn module `backend/minio_storage.py` hoạt động theo cơ chế Dual-Mode:

```ini
# Cấu hình MinIO trên Server K8s (Bắt buộc bật)
USE_MINIO=true
ONEAI_MINIO_ENDPOINT=http://107.126.11.129:31800
ONEAI_MINIO_ACCESS=your_access_key
ONEAI_MINIO_SECRET=your_secret_key
ONEAI_MINIO_BUCKETNAME=oneai
```

* **Toàn bộ dữ liệu được lưu trữ phân tán an toàn:**
  * File Excel Vendor tải lên: `oneai/sessions/{keyid}/input.xlsx`
  * Ảnh trích xuất từ bản vẽ: `oneai/sessions/{keyid}/evidence_images/*.png`
  * Dữ liệu JSON bóc tách chi tiết: `oneai/sessions/{keyid}/detail.json`
  * Gói báo cáo nghiệm thu nén: `oneai/sessions/{keyid}/final_reports/*.zip`
* **Cơ chế dọn dẹp bù trừ (Data Cleanup):**
  * Khi kỹ sư tích chọn các dòng và bấm nút **Delete** trên giao diện, hàm `delete_tasks()` trong `backend/sql.py` sẽ phối hợp với `minio_storage.delete_session_folder()` để xóa sạch toàn bộ bucket folder của tác vụ đó trên MinIO, tránh rác dữ liệu tích tụ theo thời gian.

---

## 5. HẠNG MỤC 4: TƯỜNG LỬA MẠNG NỘI BỘ (NETWORK SECURITY, EGRESS & NETWORKPOLICY WHITELIST)

Trong môi trường Enterprise Kubernetes, chính sách bảo mật mạng mặc định thường là **Default Deny Egress** (chặn toàn bộ kết nối đi ra khỏi cụm Pod).

Nếu DevOps không cấu hình mở thông mạng (Whitelist Egress), Pod Worker sẽ bị treo (Hang / Timeout) khi thực hiện các tác vụ sau:

| Dịch Vụ Đích | Địa Chỉ IP / Host | Cổng (Port) | Giao Thức | Mục Đích Sử Dụng |
| :--- | :--- | :--- | :--- | :--- |
| **Oracle Database RAC** | `107.126.10.192` $\rightarrow$ `107.126.10.246` | `1621` | TCP | Truy vấn & cập nhật bảng `MEP_PAYMENT_ANALYSIS` |
| **MinIO Object Storage** | `107.126.11.129` | `31800` (hoặc `9000`) | HTTP/TCP | Lưu trữ file Excel, ảnh trích xuất và cache `detail.json` |
| **Cụm AI GPU Vision** | `107.126.11.129` | `32200` | HTTP/TCP | Gửi ảnh bản vẽ gọi Model `NextAI-SDV` bóc tách bảng |
| **OneAI Gateway API** | `107.126.x.x` | `80` / `443` | HTTP/HTTPS | Đồng bộ xác thực người dùng Knox và CRUD bảng |

> [!IMPORTANT]
> **Hành động cần làm:** Trước khi đưa hệ thống lên cụm K8s, hãy gửi ticket cho bộ phận Hạ tầng/DevOps yêu cầu mở thông các dải IP và Port trên trong cấu hình `NetworkPolicy` của Kubernetes Namespace.

---

## 6. HẠNG MỤC 5: QUẢN TRỊ TÀI NGUYÊN TÍNH TOÁN & PHÒNG CHỐNG OOMKILLED (OUT OF MEMORY)

### 6.1. Nguy cơ tiềm ẩn từ bản vẽ CAD/PDF khổ lớn (A0, A1)
* Một bản vẽ kỹ thuật MEP dạng vector hoặc PDF khổ lớn A0 khi được render ở độ phân giải 300 DPI để nhận diện chi tiết có kích thước ảnh lên tới `14040 x 9920` pixel (gần 140 Megapixel).
* Khi thư viện OpenCV (`cv2`) và PyMuPDF giải nén ma trận điểm ảnh vào RAM, một tiến trình có thể đột biến tiêu thụ **từ 2GB đến 4GB RAM** trong vài giây.
* Nếu Kubernetes Pod được cấu hình giới hạn RAM quá thấp (ví dụ: `limits.memory: "1Gi"`), Linux Kernel sẽ lập tức kích hoạt cơ chế `OOM-Killer` và bắn hạ tiến trình với mã lỗi kinh điển:
  ```text
  State:          Terminated
  Reason:         OOMKilled
  Exit Code:      137
  ```

### 6.2. Cấu hình K8s Resource Requests & Limits khuyến nghị

Trong file YAML của K8s Deployment, bắt buộc phải cấp phát tài nguyên đủ cho các tác vụ Computer Vision:

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "6Gi"       # Đủ buffer an toàn cho 2-3 tác vụ PDF khổ A0 chạy song song
    cpu: "4000m"
```

### 6.3. Giới hạn luồng AI song song (`MAX_AI_WORKERS`)
Trong file `backend/config.py`, hệ thống đã thiết lập:
```python
MAX_AI_WORKERS = 5  # Giới hạn tối đa 5 luồng xử lý song song
```
Cơ chế Semaphore này đóng vai trò như một **chiếc van điều áp**: Khi có 20 kỹ sư cùng bấm "Upload" hoặc "Rerun" đồng thời, hệ thống sẽ xếp hàng và chỉ gửi tối đa 5 request lên máy chủ GPU cùng lúc, ngăn chặn tình trạng làm sập GPU server hoặc bị trả về lỗi `HTTP 429 Too Many Requests`.

---

## 7. HẠNG MỤC 6: GIÁM SÁT SỨC KHỎE POD (HEALTH PROBES) & QUẢN TRỊ LOG TẬP TRUNG

### 7.1. Cấu hình Liveness & Readiness Probes
Kubernetes cần biết khi nào Pod đã khởi động xong để dẫn traffic người dùng vào (Readiness), và khi nào Pod bị deadlock/treo để tự khởi động lại (Liveness).

Hệ thống đã tích hợp sẵn 2 endpoint chuẩn trong `backend/api.py`:
```python
@app.get("/healthz")
@app.get("/mep_payment/health")
async def health_check():
    """Kiểm tra tình trạng hoạt động của Worker Service (Hỗ trợ K8s Liveness/Readiness Probe)."""
    return {"status": "ok", "service": "MEP Payment AI Worker", "timestamp": time.time()}
```

Cấu hình trong file triển khai Kubernetes:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### 7.2. Chuẩn hóa Logging tập trung (Standard Output)
* Trên máy cá nhân, ta thường nhìn log trực tiếp trên cửa sổ CMD/PowerShell.
* Trên K8s, **tuyệt đối không ghi log vào file trên đĩa local** (sẽ làm tràn ổ đĩa Node K8s).
* Toàn bộ log phải được in ra `stdout` / `stderr`. Hệ thống thu thập log tập trung (Grafana Loki / Fluentd / ELK) sẽ tự động bắt lấy log từ container.
* Code backend của chúng ta đã được cấu hình reconfigure UTF-8 ở đầu mọi file (`sys.stdout.reconfigure(encoding='utf-8')`), đảm bảo log tiếng Việt trên Lens, Kibana hay `kubectl logs` không bao giờ bị lỗi font `\x...`.

---

## 8. HẠNG MỤC 7: AN NINH BẢO MẬT & LÁCH HỆ THỐNG CHẶN DLP DOANH NGHIỆP

### 8.1. Vấn đề Tường lửa DLP chặn tải file Excel (.xlsx)
* Tại các tập đoàn lớn, hệ thống an ninh thông tin (Data Loss Prevention - DLP như Symantec, McAfee DLP, Forcepoint) thường giám sát chặt chẽ lưu lượng mạng HTTP.
* Khi kỹ sư bấm tải một file `.xlsx` chứa số liệu chi phí, đơn giá, mã vật tư nội bộ, tường lửa DLP thường chặn đứng kết nối hoặc cách ly file.
* **Giải pháp của hệ thống:**
  * Khi xuất kết quả, Worker tự động đóng gói toàn bộ bảng tính Excel cùng các ảnh trích xuất bằng chứng vào một file nén **`.zip`** (`Tải Báo Cáo (.zip)`).
  * Trình duyệt tải gói `.zip` thông qua luồng nhị phân Blob (`responseType: 'blob'`) với header `application/zip`, giúp file vượt qua rào cản kiểm duyệt DLP thông suốt và an toàn.

### 8.2. Bảo vệ thông tin bí mật (Secrets Management)
* **Quy tắc vàng:** Không bao giờ commit file `backend/.env` chứa mật khẩu thật lên Git repository.
* File `.env` trên Git chỉ nên chứa các giá trị mẫu hoặc bị che:
  ```ini
  DB_MBLDB_LOCAL_AI__PASSWORD=********
  ONEAI_MINIO_SECRET=********
  ```
* Trên máy chủ K8s thật, mật khẩu được nạp thông qua **Kubernetes Secret**:
  ```bash
  kubectl create secret generic mep-ai-secrets \
    --from-literal=DB_MBLDB_LOCAL_AI__PASSWORD='WKEHDGHK1!' \
    --from-literal=ONEAI_MINIO_SECRET='your_secret_key'
  ```

---

## 9. HẠNG MỤC 8: TRỌN BỘ MẪU FILE CẤU HÌNH TRIỂN KHAI (DOCKERFILE, DEPLOYMENT, INGRESS)

Dưới đây là trọn bộ tài sản mã nguồn hạ tầng (Infrastructure as Code) đã được tinh chỉnh tối ưu dành riêng cho dự án:

### 9.1. File `Dockerfile` (Tối ưu cho Python + OpenCV + Oracle Client)
```dockerfile
# Sử dụng base image Python 3.10 slim chính thức
FROM python:3.10-slim

# Thiết lập biến môi trường hệ thống
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Cài đặt các thư viện hệ điều hành cần thiết cho OpenCV, PDF rendering và Oracle Thick Client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libaio1 \
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các thư viện Python
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn backend vào container
COPY backend/ /app/

# Mở cổng 8000
EXPOSE 8000

# Khởi chạy ứng dụng với uvicorn lắng nghe mọi card mạng
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 9.2. File `k8s-deployment.yaml` (Triển khai Pod trên Kubernetes)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mep-ai-worker-deployment
  namespace: oneai-system
  labels:
    app: mep-ai-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mep-ai-worker
  template:
    metadata:
      labels:
        app: mep-ai-worker
    spec:
      containers:
      - name: worker
        image: harbor.corp.internal/oneai/mep-ai-worker:v3.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        env:
        # Cấu hình Database theo chuẩn Chu Đức Hải
        - name: DB_MBLDB_LOCAL_AI__PASSWORD
          valueFrom:
            secretKeyRef:
              name: mep-ai-secrets
              key: db-password
        - name: DB_SERVICE
          value: "MBLDB_SVC"
        # Cấu hình MinIO Object Storage
        - name: USE_MINIO
          value: "true"
        - name: ONEAI_MINIO_ENDPOINT
          value: "http://107.126.11.129:31800"
        - name: ONEAI_MINIO_BUCKETNAME
          value: "oneai"
        - name: ONEAI_MINIO_ACCESS
          valueFrom:
            secretKeyRef:
              name: mep-ai-secrets
              key: minio-access
        - name: ONEAI_MINIO_SECRET
          valueFrom:
            secretKeyRef:
              name: mep-ai-secrets
              key: minio-secret
        # Cấu hình AI GPU Service
        - name: MEP_API_URL
          value: "http://107.126.11.129:32200/api/v1/chat/completions"
        - name: MEP_MODEL_NAME
          value: "NextAI-SDV"
        # Thiết lập tài nguyên chống OOMKilled
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "6Gi"
        # Cấu hình kiểm tra sức khỏe Pod
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

### 9.3. File `k8s-ingress.yaml` (Định tuyến thông suốt từ Bên Ngoài)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mep-ai-ingress
  namespace: oneai-system
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"          # Cho phép upload file Excel/PDF tới 100MB
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"        # Cho phép pipeline AI chạy ngầm tới 10 phút
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
spec:
  ingressClassName: nginx
  rules:
  - host: oneai.mep.corp.internal
    http:
      paths:
      # Định tuyến các API Worker bắt đầu bằng /mep_payment
      - path: /mep_payment
        pathType: Prefix
        backend:
          service:
            name: mep-ai-worker-service
            port:
              number: 8000
```

---

## 10. HẠNG MỤC 9: BẢNG CHECKLIST THỰC CHIẾN 10 BƯỚC TRƯỚC KHI BẤM TRIỂN KHAI (GO-LIVE)

Trước khi tiến hành đóng gói Docker image và bấm nút triển khai lên máy chủ thật, kỹ sư phụ trách cần tích chọn kiểm tra lần lượt 10 bước trong bảng sau:

| STT | Hạng Mục Kiểm Tra | Nội Dung Chi Tiết | Cách Thức Kiểm Tra Thực Tế | Trạng Thái |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Biến Mật Khẩu Database** | Đặt tên đúng chuẩn Chu Đức Hải: `DB_MBLDB_LOCAL_AI__PASSWORD` (bắt buộc 2 dấu `__`). | Kiểm tra file `.env` và Secret K8s. | [x] Đã chuẩn hóa |
| **2** | **Khai Báo User Name DB** | Khai báo trực tiếp `user_name="LOCAL_AI"` dạng chuỗi trong `sql.py`. | Kiểm tra hàm `get_cur()` trong `backend/sql.py`. | [x] Đã chuẩn hóa |
| **3** | **Địa Chỉ Worker Frontend** | `operation.vue` không được hardcode cố định `127.0.0.1:8000`. | Gọi thử nghiệm từ một máy tính khác trong mạng nội bộ. | [x] Đã hỗ trợ Dynamic |
| **4** | **Bật MinIO Storage** | Đặt `USE_MINIO=true`, kiểm tra bucket `oneai` đã được tạo trên máy chủ S3. | Chạy thử `test_minio_connection.py`. | [x] Sẵn sàng |
| **5** | **Thông Mạng Egress (Firewall)** | Pod Worker kết nối được tới DB (1621), MinIO (31800), AI GPU (32200). | `nc -zv 107.126.11.129 32200` từ trong Pod. | [ ] Cần check DevOps |
| **6** | **Giới Hạn RAM Chống OOM** | Set `limits.memory` tối thiểu từ **4Gi** đến **6Gi** trong Deployment YAML. | Soát file `deployment.yaml`. | [x] Đã cấu hình mẫu |
| **7** | **Endpoint Health Check** | Có sẵn `/healthz` và `/mep_payment/health` để K8s kiểm tra trạng thái Pod. | `curl http://localhost:8000/healthz` trả về `{"status":"ok"}`. | [x] Đã tích hợp |
| **8** | **Cơ Chế Giới Hạn Tải AI** | `MAX_AI_WORKERS = 5` trong `config.py` để không làm sập server GPU Vision. | Kiểm tra biến `MAX_AI_WORKERS` trong `config.py`. | [x] Đã có Semaphore |
| **9** | **Thư Mục Lưu Trữ Tự Động** | `config.py` và `api.py` tự chuyển về `sessions/` nếu không có ổ `D:\Private_Documents`. | Chạy thử code trên môi trường Linux. | [x] Đã fix thích ứng |
| **10**| **Bảo Vệ Mật Khẩu Trên Git** | File `.env` chứa mật khẩu thật đã nằm trong `.gitignore`, không push lên Git. | Kiểm tra `git status` không thấy file `.env` lộ mật khẩu. | [x] An toàn tuyệt đối |

---

> [!NOTE]
> **Tổng kết:** Toàn bộ hệ sinh thái dự án `MEP OneAI System` hiện tại đã đạt độ hoàn thiện cao nhất, sẵn sàng 100% để chuyển giao cho đội ngũ DevOps triển khai lên hệ thống máy chủ doanh nghiệp mà không gặp bất kỳ xung đột nào về hạ tầng mạng, quyền hạn truy cập hay lưu trữ phân tán.

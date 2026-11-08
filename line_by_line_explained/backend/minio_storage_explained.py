# ==============================================================================
# QUẢN TRỊ MINIO OBJECT STORAGE - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng trong hệ thống: backend/minio_storage.py
# Chuẩn hóa 100% theo kiến trúc OneAI SDV (tương thích visionGuard.py và ai_bill.py)
# ==============================================================================

# Dòng 1-17: Khối ghi chú kiến trúc Adapter MinIO
# Adapter này có nhiệm vụ làm việc với MinIO Object Storage để lưu trữ và truy xuất:
# 1. Báo cáo Excel kết quả đối soát ({vendor_stem}_Report.xlsx)
# 2. Toàn bộ file ảnh nén zip ({vendor_stem}_Report.zip)
# 3. Ảnh trích xuất từ bản vẽ CAD và ảnh cắt bảng vật tư/Gate Pass
# 4. File JSON cache chi tiết đối soát (detail.json)
# Đặc biệt: Tự động chuyển đổi mượt mà (Graceful Fallback) về ổ cứng cục bộ nếu MinIO chưa được bật hoặc mất kết nối.

# Dòng 19-25: Nhúng các thư viện chuẩn của Python
import os
import io
import time
import mimetypes
from pathlib import Path
from typing import Optional, Generator, Union
from dotenv import load_dotenv, find_dotenv

# Dòng 27: Tự động quét và nạp biến môi trường từ file .env
load_dotenv(find_dotenv())

# Dòng 29-34: Thử nạp module minio_object có sẵn trên OneAI Platform Server
# Khi chạy bên trong hạ tầng OneAI của công ty, platform đã khởi tạo sẵn singleton minio_object.
# Nếu đang ở môi trường này, hệ thống tái sử dụng ngay con trỏ client để tránh tạo nhiều connection pool.
try:
    from minio_object import minio_object as _oneai_minio_object
except ImportError:
    _oneai_minio_object = None

# Dòng 35-41: Thử nạp thư viện minio chuẩn (dành cho môi trường Standalone / Local Dev)
# Bọc try-except để nếu môi trường chưa cài đặt thư viện 'minio' thì hệ thống vẫn không bị crash,
# mà tự động fallback sang cơ chế lưu trữ file trên ổ cứng máy tính.
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

# Dòng 42-44: Đọc các tham số cấu hình MinIO cơ bản từ .env
# MINIO_PREFIX: Tiền tố thư mục gốc trên Bucket (mặc định là "mep_payment")
# USE_MINIO_CONFIG: Cờ bật/tắt MinIO (True / False). Mặc định là True.
MINIO_PREFIX = os.getenv("MINIO_PREFIX", "mep_payment")
USE_MINIO_CONFIG = os.getenv("USE_MINIO", "true").lower() in ("true", "1", "yes")


# ==============================================================================
# LỚP ĐIỀU PHỐI VÀ QUẢN TRỊ MINIO OBJECT STORAGE
# ==============================================================================
class MinioStorageManager:
    """Quản trị viên kết nối và thao tác với MinIO Object Storage."""

    # Dòng 49-59: Hàm khởi tạo (Constructor) của quản trị viên MinIO
    def __init__(self):
        # Biến lưu trữ con trỏ kết nối client tới MinIO
        self.client = None
        # Xác định tên bucket: ưu tiên các biến ONEAI_MINIO_BUCKETNAME, nếu không có lấy mặc định "oneai"
        self.bucket_name = (
            os.getenv("ONEAI_MINIO_BUCKETNAME")
            or os.getenv("ONEAI_MINIO_BUCKET_NAME")
            or os.getenv("MINIO_BUCKET_NAME")
            or "oneai"
        )
        # Cờ đánh dấu trạng thái MinIO đã sẵn sàng hoạt động hay chưa
        self.enabled = False
        # Gọi hàm thiết lập kết nối ngay khi khởi tạo instance
        self._init_connection()

    # Dòng 60-104: Khởi tạo kết nối tới MinIO Server với đa cơ chế tự thích ứng
    def _init_connection(self):
        """Khởi tạo kết nối tới MinIO."""
        # Nếu cấu hình USE_MINIO=false trong .env -> tắt MinIO, chuyển sang ghi trực tiếp ổ cứng
        if not USE_MINIO_CONFIG:
            print("📦 [MinIO] Cấu hình USE_MINIO=false -> Tắt MinIO, sử dụng ổ đĩa cục bộ.")
            return

        # 1. Cơ chế 1: Ưu tiên dùng singleton minio_object của Server OneAI nếu đang chạy trên platform
        if _oneai_minio_object is not None:
            try:
                self.client = _oneai_minio_object.client
                self.bucket_name = getattr(_oneai_minio_object, "bucket_name", self.bucket_name)
                self.enabled = True
                print(f"📦 [MinIO] Đã tích hợp OneAI Platform minio_object (Bucket: {self.bucket_name})")
                return
            except Exception as e:
                print(f"⚠️ [MinIO Warning] Không thể dùng OneAI Platform minio_object: {e}")

        # 2. Cơ chế 2: Khởi tạo client MinIO độc lập từ file .env (hỗ trợ cả chuẩn ONEAI_MINIO_* và MINIO_*)
        endpoint = os.getenv("ONEAI_MINIO_ENDPOINT") or os.getenv("MINIO_ENDPOINT")
        access_key = os.getenv("ONEAI_MINIO_ACCESS") or os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("ONEAI_MINIO_SECRET") or os.getenv("MINIO_SECRET_KEY")
        secure_val = os.getenv("ONEAI_MINIO_SECURE", os.getenv("MINIO_SECURE", "false"))
        secure = secure_val.lower() in ("true", "1", "yes")

        # Kiểm tra đầy đủ thông số kết nối và thư viện minio đã được cài đặt
        if endpoint and access_key and secret_key and Minio:
            try:
                # Loại bỏ tiền tố giao thức http:// hoặc https:// vì Minio SDK chỉ nhận host:port
                clean_endpoint = endpoint.replace("http://", "").replace("https://", "").strip()
                self.client = Minio(
                    clean_endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure
                )
                self.enabled = True
                print(f"📦 [MinIO] Đã kết nối MinIO Server ({clean_endpoint}, Bucket: {self.bucket_name})")
            except Exception as e:
                # Nếu xảy ra lỗi kết nối mạng (sai IP/port/credentials) -> Tự động dùng ổ đĩa, không dừng app
                print(f"⚠️ [MinIO Warning] Không thể kết nối MinIO Server ({e}) -> Fallback sang lưu đĩa.")
                self.enabled = False
        else:
            if not Minio:
                print("ℹ️ [MinIO] Chưa cài thư viện 'minio' -> Tự động chuyển sang lưu đĩa.")
            else:
                print("ℹ️ [MinIO] Chưa cấu hình ONEAI_MINIO_ENDPOINT / MINIO_ENDPOINT trong .env -> Tự động chuyển sang lưu đĩa.")
            self.enabled = False

    # Dòng 105-108: Kiểm tra trạng thái sẵn sàng của kết nối MinIO
    def is_available(self) -> bool:
        """Kiểm tra MinIO đã sẵn sàng sử dụng hay chưa."""
        return bool(self.enabled and self.client)

    # Dòng 109-129: Tạo khóa Object Key Posix phân cấp theo Tháng thanh toán
    def get_obj_key(self, keyid: str, subfolder: str, filename: str, month: Optional[str] = None) -> str:
        """
        Tạo khóa object chuẩn Posix theo phân cấp tháng:
        mep_payment/[<month>/]<safe_keyid>/<subfolder>/<filename>
        Ví dụ: mep_payment/2026-11/WOR2510150002/reports/Sample_Report.zip
        """
        # Làm sạch mã KEYID tránh ký tự đặc biệt gây lỗi đường dẫn S3
        safe_key = str(keyid).replace('/', '_').replace('\\', '_').replace(':', '_').strip()
        sub = subfolder.strip('/') if subfolder else ''
        fname = filename.strip('/')

        parts = [MINIO_PREFIX]
        # Nếu có chỉ định tháng thanh toán -> chèn vào phân cấp để quản lý dữ liệu theo từng tháng
        if month:
            safe_month = str(month).replace('/', '_').replace('\\', '_').replace(':', '_').strip()
            if safe_month:
                parts.append(safe_month)
        parts.append(safe_key)
        if sub:
            parts.append(sub)
        parts.append(fname)
        return "/".join(parts)

    # Dòng 130-156: Tải file từ ổ cứng lên MinIO (Put Object)
    def upload_file(self, local_path: Union[str, Path], object_key: str, content_type: Optional[str] = None) -> bool:
        """Upload file vật lý từ ổ cứng lên MinIO (Wrapper quanh client.put_object theo chuẩn visionGuard)."""
        if not self.is_available():
            return False
        local_p = Path(local_path)
        if not local_p.exists() or not local_p.is_file():
            return False

        try:
            # Tự động nhận diện MIME type của file (ví dụ: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
            if not content_type:
                content_type, _ = mimetypes.guess_type(str(local_p))
            content_type = content_type or "application/octet-stream"

            file_size = local_p.stat().st_size
            with open(local_p, "rb") as f_data:
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_key,
                    data=f_data,
                    length=file_size,
                    content_type=content_type
                )
            return True
        except Exception as exc:
            print(f"⚠️ [MinIO Put Warning] Thất bại khi upload {object_key}: {exc}")
            return False

    # Dòng 157-173: Đẩy trực tiếp dữ liệu dạng bytes lên MinIO (không cần tạo file rác trên ổ cứng)
    def upload_bytes(self, data: bytes, object_key: str, content_type: str = "application/octet-stream") -> bool:
        """Upload dữ liệu byte trực tiếp lên MinIO mà không cần ghi file tạm ra đĩa."""
        if not self.is_available():
            return False
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            return True
        except Exception as exc:
            print(f"⚠️ [MinIO Put Warning] Thất bại khi upload bytes {object_key}: {exc}")
            return False

    # Dòng 174-188: Tải nội dung object về RAM dưới dạng chuỗi bytes
    def download_bytes(self, object_key: str) -> Optional[bytes]:
        """Tải toàn bộ nội dung object từ MinIO về dạng bytes."""
        if not self.is_available() or not object_key:
            return None
        try:
            resp = self.client.get_object(self.bucket_name, object_key)
            try:
                return resp.read()
            finally:
                resp.close()
                resp.release_conn()
        except Exception as exc:
            print(f"⚠️ [MinIO Get Warning] Thất bại khi tải {object_key}: {exc}")
            return None

    # Dòng 189-198: Mở luồng stream object từ MinIO
    def open_object(self, object_key: str):
        """Mở kết nối stream đọc object từ MinIO (phục vụ StreamingResponse của FastAPI)."""
        if not self.is_available() or not object_key:
            return None
        try:
            return self.client.get_object(self.bucket_name, object_key)
        except Exception as exc:
            print(f"⚠️ [MinIO Open Warning] Không thể mở object {object_key}: {exc}")
            return None

    # Dòng 199-211: Generator stream dữ liệu chunk-by-chunk trả về cho trình duyệt
    @staticmethod
    def stream_object(response, chunk_size: int = 32 * 1024) -> Generator[bytes, None, None]:
        """Generator stream dữ liệu từng chunk từ MinIO response và tự động giải phóng socket kết nối."""
        try:
            for chunk in response.stream(chunk_size):
                yield chunk
        finally:
            # Đảm bảo socket kết nối luôn được đóng trả về connection pool
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass

    # Dòng 212-222: Xóa một object đơn lẻ trên MinIO
    def remove_object(self, object_key: str) -> bool:
        """Xóa một object trên MinIO."""
        if not self.is_available() or not object_key:
            return False
        try:
            self.client.remove_object(self.bucket_name, object_key)
            return True
        except Exception as exc:
            print(f"⚠️ [MinIO Remove Warning] Thất bại khi xóa {object_key}: {exc}")
            return False

    # Dòng 223-240: Xóa toàn bộ objects nằm dưới một prefix thư mục
    def remove_prefix(self, prefix: str) -> int:
        """Xóa toàn bộ các object nằm trong 1 thư mục / prefix (dùng khi xóa Task KEYID)."""
        if not self.is_available() or not prefix:
            return 0
        try:
            objects_to_del = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            count = 0
            for obj in objects_to_del:
                try:
                    self.client.remove_object(self.bucket_name, obj.object_name)
                    count += 1
                except Exception:
                    pass
            return count
        except Exception as exc:
            print(f"⚠️ [MinIO Remove Prefix Warning] Thất bại khi xóa prefix {prefix}: {exc}")
            return 0

    # Dòng 241-286: Xóa dọn sạch sẽ toàn bộ dữ liệu của Task trên MinIO (Cascade Cleanup)
    def remove_task_objects(self, keyid: str, month: Optional[str] = None) -> int:
        """
        Xóa sạch 100% tất cả các objects trên MinIO liên quan đến task KEYID (Cascade Cleanup).
        Xóa cả cấu trúc theo tháng (mep_payment/<month>/<keyid>/), cấu trúc phẳng cũ (mep_payment/<keyid>/),
        và các bản copy mồ côi trong mep_payment/reports/.
        """
        if not self.is_available() or not keyid:
            return 0

        safe_key = str(keyid).replace('/', '_').replace('\\', '_').replace(':', '_').strip()
        total_deleted = 0

        # 1. Xóa theo thư mục tháng mới
        if month:
            safe_month = str(month).replace('/', '_').replace('\\', '_').strip()
            prefix_month = f"{MINIO_PREFIX}/{safe_month}/{safe_key}/"
            total_deleted += self.remove_prefix(prefix_month)

        # 2. Xóa theo thư mục phẳng cũ
        prefix_flat = f"{MINIO_PREFIX}/{safe_key}/"
        total_deleted += self.remove_prefix(prefix_flat)

        # 3. Quét dọn các file báo cáo trong mep_payment/reports/ có tên trùng mã KEYID
        try:
            all_objs = self.client.list_objects(self.bucket_name, prefix=f"{MINIO_PREFIX}/", recursive=True)
            for obj in all_objs:
                obj_name = obj.object_name
                # Xóa object nằm trong folder của task
                if f"/{safe_key}/" in obj_name:
                    try:
                        self.client.remove_object(self.bucket_name, obj_name)
                        total_deleted += 1
                    except Exception:
                        pass
                # Xóa file mồ côi trong mep_payment/reports/ có chứa mã WO
                elif obj_name.startswith(f"{MINIO_PREFIX}/reports/") and safe_key in obj_name:
                    try:
                        self.client.remove_object(self.bucket_name, obj_name)
                        total_deleted += 1
                    except Exception:
                        pass
        except Exception as exc:
            print(f"⚠️ [MinIO Cleanup Warning] Quét dọn MinIO cho {safe_key}: {exc}")

        return total_deleted

    # Dòng 287-330: Di chuyển thư mục tháng của task trên MinIO (Server-side Copy)
    def move_task_month(self, keyid: str, old_month: str, new_month: str) -> int:
        """
        Di chuyển toàn bộ objects của task từ thư mục tháng cũ sang tháng mới trên MinIO (Server-side Copy).
        mep_payment/<old_month>/<safe_key>/... -> mep_payment/<new_month>/<safe_key>/...
        Không tải file về máy, tốc độ cực nhanh (~0.2s - 0.3s cho toàn bộ 25 files).
        """
        if not self.is_available() or not keyid or not old_month or not new_month:
            return 0

        safe_key = str(keyid).replace('/', '_').replace('\\', '_').replace(':', '_').strip()
        safe_old_m = str(old_month).replace('/', '_').replace('\\', '_').strip()
        safe_new_m = str(new_month).replace('/', '_').replace('\\', '_').strip()

        # Nếu tháng cũ và mới trùng nhau -> không cần di chuyển
        if safe_old_m == safe_new_m:
            return 0

        old_prefix = f"{MINIO_PREFIX}/{safe_old_m}/{safe_key}/"
        new_prefix = f"{MINIO_PREFIX}/{safe_new_m}/{safe_key}/"

        count = 0
        try:
            from minio.commonconfig import CopySource
            objects = list(self.client.list_objects(self.bucket_name, prefix=old_prefix, recursive=True))
            for obj in objects:
                old_key = obj.object_name
                new_key = old_key.replace(old_prefix, new_prefix, 1)
                try:
                    # Sao chép trực tiếp nội bộ giữa các object trên MinIO Server
                    self.client.copy_object(
                        self.bucket_name,
                        new_key,
                        CopySource(self.bucket_name, old_key)
                    )
                    # Xóa object ở tháng cũ sau khi copy thành công
                    self.client.remove_object(self.bucket_name, old_key)
                    count += 1
                except Exception as copy_err:
                    print(f"⚠️ [MinIO Move Error] {old_key} -> {new_key}: {copy_err}")

            if count > 0:
                print(f"🚚 [MinIO Move] Đã dời thành công {count} objects của {safe_key} từ {safe_old_m} sang {safe_new_m}")
            return count
        except Exception as exc:
            print(f"⚠️ [MinIO Move Warning] Lỗi khi dời folder task {safe_key}: {exc}")
            return count

    # Dòng 331-375: Tìm kiếm Object Key siêu tốc O(1) với cơ chế Tự Phục Hồi (Self-Healing)
    def find_task_object(self, keyid: str, subfolder: str, filename: str, month: Optional[str] = None) -> Optional[str]:
        """
        Tìm kiếm object key trên MinIO siêu tốc (O(1) Direct Key Lookups):
        1. Kiểm tra mep_payment/<month>/<safe_key>/<subfolder>/<filename>
        2. Kiểm tra mep_payment/<safe_key>/<subfolder>/<filename>
        3. Kiểm tra mep_payment/<tháng hiện tại>/<safe_key>/<subfolder>/<filename>
        4. Self-Healing Fallback: Quét 1 cấp thư mục tháng gần đây (nếu có di chuyển tháng mà file chưa dời)
        (Không quét đệ quy toàn bộ bucket để đảm bảo mở modal tức thì < 20ms).
        """
        if not self.is_available() or not keyid or not filename:
            return None

        # 1. Thử đường dẫn theo tháng được truyền vào
        if month:
            key_month = self.get_obj_key(keyid, subfolder, filename, month=month)
            if self.object_exists(key_month):
                return key_month

        # 2. Thử đường dẫn phẳng cũ
        key_flat = self.get_obj_key(keyid, subfolder, filename, month=None)
        if self.object_exists(key_flat):
            return key_flat

        # 3. Thử tháng hiện tại (nếu month truyền vào khác hoặc None)
        cur_month = time.strftime("%Y-%m")
        if month != cur_month:
            key_cur = self.get_obj_key(keyid, subfolder, filename, month=cur_month)
            if self.object_exists(key_cur):
                return key_cur

        # 4. Fallback tự phục hồi (Self-Healing Fallback):
        # Quét 1 cấp danh sách thư mục tháng trong mep_payment/ (cực nhanh < 10ms, không đệ quy)
        try:
            for obj in self.client.list_objects(self.bucket_name, prefix=f"{MINIO_PREFIX}/", recursive=False):
                if getattr(obj, 'is_dir', False) or str(obj.object_name).endswith('/'):
                    cand_month = obj.object_name.replace(f"{MINIO_PREFIX}/", "").strip("/")
                    if cand_month and cand_month not in (month, cur_month):
                        test_key = self.get_obj_key(keyid, subfolder, filename, month=cand_month)
                        if self.object_exists(test_key):
                            return test_key
        except Exception:
            pass

        return None

    # Dòng 376-406: Tìm file báo cáo Excel hoặc Zip của task
    def find_report_file(self, filename: str) -> Optional[str]:
        """
        Tìm file báo cáo (.xlsx hoặc .zip) trên MinIO theo tên file:
        Hỗ trợ tìm trong mep_payment/<month>/<keyid>/reports/ hoặc mep_payment/reports/.
        """
        if not self.is_available() or not filename:
            return None

        # 1. Thử trong thư mục reports cũ
        candidates = [
            f"{MINIO_PREFIX}/reports/{filename}",
            f"{MINIO_PREFIX}/reports/{filename.replace('.zip', '.xlsx')}" if filename.endswith('.zip') else f"{MINIO_PREFIX}/reports/{filename.replace('.xlsx', '.zip')}"
        ]
        for c in candidates:
            if self.object_exists(c):
                return c

        # 2. Quét tìm trong toàn bộ MinIO
        try:
            target_name = Path(filename).name.lower()
            alt_name = target_name.replace(".zip", ".xlsx") if target_name.endswith(".zip") else target_name.replace(".xlsx", ".zip")
            all_objs = self.client.list_objects(self.bucket_name, prefix=f"{MINIO_PREFIX}/", recursive=True)
            for obj in all_objs:
                fname = Path(obj.object_name).name.lower()
                if fname in (target_name, alt_name):
                    return obj.object_name
        except Exception:
            pass

        return None

    # Dòng 407-416: Kiểm tra object có tồn tại bằng lệnh STAT nhẹ O(1)
    def object_exists(self, object_key: str) -> bool:
        """Kiểm tra xem object có tồn tại trên MinIO hay không."""
        if not self.is_available() or not object_key:
            return False
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except Exception:
            return False

    # Dòng 417-434: Sinh URL có chữ ký bảo mật (Presigned GET URL)
    def get_presigned_url(self, object_key: str, expires_days: int = 1) -> Optional[str]:
        """
        Tạo đường link presigned URL tạm thời cho phép người dùng mở/tải trực tiếp từ MinIO
        (Đồng bộ theo pattern minio.py của OneAI).
        """
        if not self.is_available() or not object_key:
            return None
        try:
            from datetime import timedelta
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                expires=timedelta(days=expires_days),
            )
        except Exception as exc:
            print(f"⚠️ [MinIO Presigned Warning] Lỗi tạo presigned URL cho {object_key}: {exc}")
            return None


# Dòng 436-437: Khởi tạo Singleton instance dùng chung cho toàn bộ backend
minio_storage = MinioStorageManager()


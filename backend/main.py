# ====================================================================
# LAUNCHER SERVICE (MEP PAYMENT AI WORKER)
# File: backend/main.py
# Khởi động FastAPI Worker Server và luồng giám sát dọn dẹp tự động
# ====================================================================
import os
import sys
import time
import shutil
import threading
from pathlib import Path
import uvicorn

# CẤU HÌNH CỔNG VÀ HOST
HOST = os.getenv("WORKER_HOST", "0.0.0.0")
PORT = int(os.getenv("WORKER_PORT", 8000))

def start_api():
    """Khởi chạy máy chủ FastAPI Worker."""
    print(f"🚀 [FastAPI] Khởi động Worker tại http://{HOST}:{PORT} ...")
    uvicorn.run(
        "api:app",
        host=HOST,
        port=PORT,
        reload=False
    )

def cleanup_old_sessions(storage_dir: Path, max_days: int = 30):
    """Tự động dọn dẹp các thư mục phiên làm việc cũ sau 30 ngày."""
    if not storage_dir.exists():
        return
    now = time.time()
    cutoff = now - (max_days * 86400)
    
    for item in storage_dir.glob("session_*"):
        if item.is_dir() and item.stat().st_mtime < cutoff:
            try:
                print(f"🧹 [Auto Cleanup] Đang xóa thư mục phiên cũ: {item.name}")
                shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                print(f"⚠️ [Cleanup Warning] Không thể xóa {item.name}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🌟 MEP PAYMENT AI WORKER SERVICE - LAUNCHER")
    print("=" * 60)

    # 1. Khởi động API Server ở thread riêng (daemon thread)
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    storage_dir = Path(__file__).resolve().parent / "sessions"

    # 2. Luồng chính giám sát và dọn dẹp định kỳ
    print("✅ Service đã sẵn sàng tiếp nhận yêu cầu từ OneAI Portal...")
    while True:
        try:
            cleanup_old_sessions(storage_dir, max_days=30)
        except Exception as err:
            print(f"⚠️ Lỗi trong vòng lặp bảo trì: {err}")
        
        # Kiểm tra dọn dẹp mỗi 6 tiếng một lần
        time.sleep(6 * 3600)


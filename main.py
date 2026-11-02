
import time
from pathlib import Path
from datetime import datetime, timedelta
from eqp_scheduler import eqp_scheduler_daily
import threading
import uvicorn
from  folder_check import monitor_folder
             
def start_api():
    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
   
    # Khởi động API ở thread riêng
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    print("Service started...")
   
    # Chạy ngay khi khởi động
    print("Run daily scheduler (startup)...")
    eqp_scheduler_daily()

    # Lần chạy đầu tiên: 00:00 ngày mai
    next_daily = datetime.combine(
        datetime.now().date() + timedelta(days=1),
        datetime.min.time()
    )
    while True:

        # Chạy job hàng ngày
        if datetime.now() >= next_daily:
            print("Run daily scheduler...")
            eqp_scheduler_daily()
            next_daily += timedelta(days=1)

        # Xử lý file
        processed = monitor_folder()

        # Chỉ nghỉ khi không có file
        if not processed:
            print("No file. Sleep 30s...")
            time.sleep(30)
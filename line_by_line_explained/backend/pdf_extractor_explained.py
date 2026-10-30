# ==============================================================================
# TRÁI TIM THỊ GIÁC AI - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/pdf_extractor.py
# ==============================================================================

# Dòng 1-18: Nhúng các thư viện khoa học dữ liệu và xử lý hình ảnh
import os                       # Thao tác thư mục, file
import re                       # Biểu thức chính quy tách chuỗi và regex số bản vẽ
import time                     # Đo thời gian gọi AI
import json                     # Phân tích cú pháp JSON AI trả về
import base64                   # Mã hóa ảnh sang chuỗi ký tự Base64 để gửi qua HTTP
import requests                 # Gửi HTTP Request lên AI Vision Endpoint
import glob                     # Quét danh sách file
import concurrent.futures       # Xử lý ĐA LUỒNG (Multi-threading) song song

import fitz                     # PyMuPDF: Đọc và render trang PDF sang ảnh cực nhanh
import cv2                      # OpenCV: Xử lý ảnh, bộ lọc hình thái học, cắt bảng
import numpy as np              # Thao tác ma trận điểm ảnh (pixel arrays)
import pandas as pd             # Xử lý bảng dữ liệu trung gian DataFrame

import config                   # Cấu hình hệ thống
import utils as ut              # Hàm làm sạch tên file tiếng Việt

# ==============================================================================
# KHỐI 1: XỬ LÝ CASE 1 (BẢNG EXCEL DÁN OLE VÀO BẢN VẼ CAD)
# ==============================================================================

def _score_horizontal_lines(img):
    """
    HÀM CHẤM ĐIỂM ĐƯỜNG KẺ NGANG:
    Mục đích: Xác định xem một bức ảnh nhúng có phải là BẢNG BIỂU hay không.
    Nguyên lý: Áp dụng phép lọc hình thái học (Morphology Open) với phần tử cấu trúc ngang (50x1).
    Chỉ những đối tượng là đường kẻ ngang thẳng tắp của bảng mới giữ lại được.
    Đếm tổng số điểm ảnh sáng (pixel > 0). Điểm càng cao -> Chắc chắn là Bảng!
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
    return np.sum(horizontal_lines > 0)

def _render_bbox_to_cv2(page, rect, dpi=250):
    """
    HÀM CẮT TỌA ĐỘ VÀ RENDER SANG ẢNH OPENCV:
    Lấy vùng Rect (x0, y0, x1, y1) trên trang PDF, render ở độ phân giải 250 DPI
    và chuyển đổi từ định dạng mẫu PyMuPDF sang mảng numpy BGR chuẩn của OpenCV.
    """
    pix = page.get_pixmap(clip=rect, dpi=dpi)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

def extract_table_from_embedded_image(doc, page):
    """
    HÀM TRÍCH XUẤT CASE 1 (HYBRID FAST-MODE):
    1. Nhánh Fast-mode: Trong AutoCAD, khi kỹ sư dán bảng Excel vào, ảnh bảng thường nằm ở vị trí index [1].
       Hàm kiểm tra ngay ảnh index [1], nếu _score_horizontal_lines >= 1000 -> Bắt luôn, không cần quét tiếp.
    2. Nhánh Fallback: Nếu index [1] không phải là bảng, hàm sẽ quét toàn bộ danh sách ảnh nhúng
       và chọn ra ảnh có điểm đường kẻ ngang cao nhất.
    """
    image_info_list = page.get_image_info(xrefs=True)
    if not image_info_list: return []
    page_area = page.rect.width * page.rect.height
    use_fast_mode = getattr(config, 'OLE_FAST_MODE', True)

    if use_fast_mode and len(image_info_list) >= 2:
        bbox = image_info_list[1]["bbox"]
        rect = fitz.Rect(bbox)
        if rect.width >= 50 and rect.height >= 50 and (rect.width * rect.height) / page_area <= 0.8:
            img_fast = _render_bbox_to_cv2(page, rect, dpi=250)
            if _score_horizontal_lines(img_fast) >= 1000:
                return [img_fast]

    best_img = None
    max_line_score = 0
    for img_info in image_info_list:
        bbox = img_info["bbox"]
        if bbox[2] - bbox[0] < 50 or bbox[3] - bbox[1] < 50: continue
        rect = fitz.Rect(bbox)
        if (rect.width * rect.height) / page_area > 0.8: continue
        img = _render_bbox_to_cv2(page, rect, dpi=250)
        score = _score_horizontal_lines(img)
        if score > max_line_score:
            max_line_score = score
            best_img = img

    if max_line_score >= 1000 and best_img is not None:
        return [best_img]
    return []

# ==============================================================================
# KHỐI 2: XỬ LÝ CASE 2 & GATE PASS (THUẬT TOÁN MAGIC CROP BẢN VẼ CAD THUẦN)
# ==============================================================================

def extract_table_native_cad(doc, page, is_gate_pass=False):
    """
    THUẬT TOÁN MAGIC CROP ĐA MỎ NEO:
    1. Tìm tọa độ các chữ mỏ neo (Q'TY, Item code, Phụ trội...) trên trang PDF.
    2. Render trang PDF ở 200 DPI và lọc các đường kẻ ngang bằng Morphology (kernel 150x1).
    3. Giãn nở (Dilate 50x80) để hợp nhất các đường kẻ thành khối hộp bao quanh bảng.
    4. Định vị khối hộp nào bao quanh các mỏ neo chữ -> Xác định chính xác vị trí Bảng.
    5. Gọt viền thừa (Shave & Shink): Quét các đường kẻ bên trong để gọt bỏ phần nét vẽ kỹ thuật
       hoặc chữ ký thừa xung quanh bảng.
    """
    anchor_keywords = ["Item code", "Tên Vật Tư", "Số Lượng"] if is_gate_pass else ["Specification", "Q'TY", "Item Code", "Item code"]
    dpi = 200
    pix = page.get_pixmap(dpi=dpi)
    scale_x = pix.width / page.rect.width
    scale_y = pix.height / page.rect.height

    anchor_centers = []
    for kw in anchor_keywords:
        text_instances = page.search_for(kw)
        if text_instances:
            for rect in text_instances:
                cx = (rect.x0 + rect.x1) / 2 * scale_x
                cy = (rect.y0 + rect.y1) / 2 * scale_y
                anchor_centers.append((cx, cy))

    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    img = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    h_img, w_img = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (150, 1))
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)

    # Xóa viền khung giấy
    contours_h, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_h:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > w_img * 0.85: cv2.drawContours(h_lines, [cnt], -1, 0, -1)

    table_mask = cv2.dilate(h_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (50, 80)), iterations=1)
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    valid_bboxes = []
    if anchor_centers:
        for ax, ay in anchor_centers:
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w < 300 or h < 50: continue
                if (x - 80 <= ax <= x + w + 80) and (y - 80 <= ay <= y + h + 80):
                    valid_bboxes.append({"bbox": (x, y, w, h), "anchor": (ax, ay)})
                    break

    # Lọc bỏ bounding box trùng
    unique_bboxes, seen = [], set()
    for item in valid_bboxes:
        if item["bbox"] not in seen:
            seen.add(item["bbox"]); unique_bboxes.append(item)

    if not unique_bboxes: return []

    extracted_tables = []
    for item in unique_bboxes:
        x, y, w, h = item["bbox"]
        pad = 20
        x_crop, y_crop = max(0, x - pad), max(0, y - pad)
        w_crop, h_crop = min(img.shape[1] - x_crop, w + 2 * pad), min(img.shape[0] - y_crop, h + 2 * pad)
        extracted_tables.append(img[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop])

    return extracted_tables

# ==============================================================================
# KHỐI 3: TRẠM ĐIỀU PHỐI (DISPATCHER) & ĐỌC SỐ BẢN VẼ
# ==============================================================================

def is_gate_pass_page(page, force_mode=None):
    """Kiểm tra xem trang hiện tại có phải Biên bản vật tư mang vào (Gate Pass) không."""
    if force_mode == "gate_pass": return True
    if force_mode == "drawing": return False
    page_text = page.get_text("text").upper()
    return any(m in page_text for m in ["VẬT TƯ MANG VÀO", "THÔNG TIN CHI TIẾT HÀNG MANG VÀO", "TÊN VẬT TƯ"])

def get_table_image_from_page(doc, page, force_mode=None):
    """Hàm trạm trưởng: Điều phối phân luồng chính xác giữa Gate Pass, Case 1 và Case 2."""
    if is_gate_pass_page(page, force_mode):
        imgs = extract_table_native_cad(doc, page, is_gate_pass=True)
        return (imgs, "gate_pass") if imgs else ([], None)

    imgs = extract_table_from_embedded_image(doc, page)
    if imgs: return imgs, "case1"

    imgs = extract_table_native_cad(doc, page, is_gate_pass=False)
    if imgs: return imgs, "case2"

    return [], None

def capture_roi_image(page):
    """Cắt vùng ảnh góc dưới bên phải trang bản vẽ (nơi chứa khung tên số bản vẽ)."""
    r, roi = page.rect, config.ROI_DRAWING_NO
    clip_rect = fitz.Rect(r.width * roi[0], r.height * roi[1], r.width * roi[2], r.height * roi[3])
    pix = page.get_pixmap(clip=clip_rect, dpi=150)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

def extract_drawing_no_tier1(page):
    """Tầng 1: Đọc nhanh số bản vẽ trực tiếp bằng Text của PDF không cần gọi AI."""
    r, roi = page.rect, config.ROI_DRAWING_NO
    text = page.get_text("text", clip=fitz.Rect(r.width * roi[0], r.height * roi[1], r.width * roi[2], r.height * roi[3]))
    match = re.search(r"DRAWING\s*NO\.?([\s\S]+)", text, re.IGNORECASE) or re.search(r"BẢN\s*VẼ([\s\S]+)", text, re.IGNORECASE)
    if match:
        for line in match.group(1).split('\n'):
            line = line.strip()
            if line and not re.match(r'^(?:A[0-4]|TỶ|SCALE)', line, re.IGNORECASE):
                clean_no = re.sub(r'[^\w\-]', '', line)
                if clean_no and clean_no.upper() not in ["DRAWING", "NO"]:
                    return clean_no
    return None

# ==============================================================================
# KHỐI 4: GỌI AI VISION VỚI PROMPT CHỐNG ẢO GIÁC (ZERO HALLUCINATION)
# ==============================================================================

def encode_image(img):
    """Scale ảnh về kích thước chuẩn và encode Base64 trong bộ nhớ RAM (không ghi đĩa)."""
    h, w = img.shape[:2]
    scale = config.TARGET_IMG_HEIGHT / h if h > 0 else 1
    new_w, new_h = int(w * scale), int(h * scale)
    if new_w > config.MAX_IMG_WIDTH:
        scale = config.MAX_IMG_WIDTH / w
        new_w, new_h = int(w * scale), int(h * scale)
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    _, buffer = cv2.imencode('.jpg', img_resized, [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY])
    return base64.b64encode(buffer).decode('utf-8')

def clean_ai_dataframe(df):
    """Lọc dữ liệu sạch: Chỉ nhận mã SDAC có trên 5 ký tự và chứa dấu gạch nối '-'."""
    if df.empty: return df
    df_clean = df.copy()
    if 'SDAC_CODE' in df_clean.columns:
        df_clean['SDAC_CODE'] = df_clean['SDAC_CODE'].astype(str).str.strip().str.upper()
        df_clean = df_clean[df_clean['SDAC_CODE'].str.len() > 5]
        df_clean = df_clean[df_clean['SDAC_CODE'].str.contains(r'-', regex=True)]
    return df_clean

def call_ai_vision(task_data):
    """
    HÀM GỌI API AI VISION:
    Gửi payload JSON chứa prompt chuyên sâu và ảnh Base64 lên NextAI-SDV.
    Prompt ép AI chỉ trích xuất đúng 4 cột: SDAC_CODE (12 ký tự), QTY, PHU_TROI, REMARK ("SDV" hoặc "").
    """
    task_type = task_data["type"]
    case_type = task_data.get("case_type", "case1")
    img = task_data["img"]
    base64_image = encode_image(img)

    if task_type == "drawing_no":
        prompt = "Đọc và trả về DUY NHẤT mã số bản vẽ ở khung tên (Ví dụ: 1, 2, A-01). Không giải thích thêm."
    elif case_type == "gate_pass":
        prompt = "Trích xuất mảng JSON gồm 2 key: SDAC_CODE (Item code 12 ký tự) và QTY (Số lượng). Chỉ trả về JSON."
    else:
        prompt = """
        Trích xuất bảng MEP ra mảng JSON gồm 4 key:
        1. "SDAC_CODE": Mã dưới cột Item code/Code (LUÔN CÓ ĐÚNG 12 KÝ TỰ, ví dụ M03-21668484).
        2. "QTY": Khối lượng tổng của dòng.
        3. "PHU_TROI": Phụ trội (% ví dụ 20%).
        4. "REMARK": Chứa chữ 'SDV' hoặc ô trống. TUYỆT ĐỐI CHỈ NHẬN 'SDV' hoặc ''.
        Chỉ trả về JSON hợp lệ. Nếu ảnh không có mã hợp lệ trả về [].
        """

    payload = {
        "model": config.MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
        ]}],
        "temperature": config.TEMPERATURE
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config.API_KEY}"}

    for attempt in range(config.MAX_RETRIES):
        try:
            response = requests.post(config.API_URL, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()

            if task_type == "drawing_no":
                return {"type": "drawing_no", "data": result_text}

            start_idx = min([i for i in [result_text.find('['), result_text.find('{')] if i >= 0] or [0])
            parsed_json, _ = json.JSONDecoder().raw_decode(result_text[start_idx:])
            if isinstance(parsed_json, dict):
                parsed_json = list(parsed_json.values())[0] if parsed_json else []

            df = pd.DataFrame(parsed_json)
            if not df.empty:
                if 'QTY' in df.columns:
                    df['QTY'] = pd.to_numeric(df['QTY'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
                if case_type == "gate_pass":
                    df = df.reindex(columns=["SDAC_CODE", "QTY"]).fillna({"SDAC_CODE": "", "QTY": 0})
                else:
                    if 'REMARK' in df.columns:
                        df['REMARK'] = df['REMARK'].apply(lambda x: "SDV" if "SDV" in str(x).upper() else "")
                    df = df.reindex(columns=["SDAC_CODE", "QTY", "PHU_TROI", "REMARK"]).fillna("")
                df = clean_ai_dataframe(df)

            return {"type": "table", "data": df}
        except Exception:
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return {"type": task_type, "data": "" if task_type == "drawing_no" else pd.DataFrame()}

    return {"type": task_type, "data": "" if task_type == "drawing_no" else pd.DataFrame()}

# ==============================================================================
# KHỐI 5: XỬ LÝ TOÀN DIỆN 1 TRANG PDF (TỐI ƯU HÓA BỘ NHỚ LƯU TRỮ)
# ==============================================================================

def get_smart_cut_points_case1(img, max_chunk_height):
    """Cắt khúc Case 1: Lần theo đường kẻ ngang của Excel dán OLE để đặt vết dao cắt."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(100, w // 4), 1)))
    line_y_coords = np.where(np.sum(horizontal_lines, axis=1) > 0)[0]

    cut_points, current_y = [0], 0
    while current_y + max_chunk_height < h:
        target_y = current_y + max_chunk_height
        valid_lines = line_y_coords[(line_y_coords >= target_y - 60) & (line_y_coords <= target_y + 60)]
        best_y = valid_lines[np.argmin(np.abs(valid_lines - target_y))] if len(valid_lines) > 0 else target_y
        cut_points.append(best_y)
        current_y = best_y
    cut_points.append(h)
    return cut_points

def get_smart_cut_points_case2(img, max_chunk_height):
    """Cắt khúc Case 2: Luồn lách dao cắt qua các khe hở khoảng trắng giữa các dòng chữ."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh_dilated = cv2.dilate(thresh, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5)), iterations=1)
    row_sums = np.sum(thresh_dilated, axis=1)

    cut_points, current_y = [0], 0
    while current_y + max_chunk_height < h:
        target_y = current_y + max_chunk_height
        search_min = max(current_y + 50, target_y - 80)
        best_y, min_pixels = target_y, float('inf')
        for y in range(target_y, search_min, -1):
            if row_sums[y] < min_pixels:
                min_pixels = row_sums[y]; best_y = y
                if min_pixels == 0: break
        cut_points.append(best_y); current_y = best_y
    cut_points.append(h)
    return cut_points

def process_single_pdf(pdf_path, force_mode=None, out_drawing_dir=None, out_gatepass_dir=None, evidence_dir=None):
    """
    HÀM XỬ LÝ CHÍNH CHO 1 FILE PDF:
    - Điểm cải tiến cốt lõi: CHỈ LƯU 1-2 ẢNH BẰNG CHỨNG JPEG (quality 85) trên mỗi trang.
    - Cắt khúc nhỏ (chunks) chỉ thực hiện trực tiếp trên mảng numpy RAM, KHÔNG GHI RA Ổ CỨNG.
    - Gửi đa luồng lên AI -> Lưu kết quả bóc tách vào CSV.
    """
    file_name = os.path.basename(pdf_path)
    doc = fitz.open(pdf_path)
    base_name = ut.clean_vietnamese_filename(os.path.splitext(file_name)[0])

    dir_csv_drawings = out_drawing_dir or config.DIR_CSV_EXTRACTED
    dir_csv_gatepass = out_gatepass_dir or config.DIR_GATEPASS_CSV
    dir_evidence     = evidence_dir or config.DIR_IMG_EXTRACTED
    os.makedirs(dir_csv_drawings, exist_ok=True)
    os.makedirs(dir_csv_gatepass, exist_ok=True)
    os.makedirs(dir_evidence, exist_ok=True)

    jpeg_opts = [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY]

    for page_num in range(len(doc)):
        page = doc[page_num]
        table_imgs, case_type = get_table_image_from_page(doc, page, force_mode=force_mode)
        if not table_imgs: continue

        tasks = []
        drawing_no = None

        # 1. Lưu duy nhất 1 ảnh bằng chứng Số bản vẽ (chỉ 30KB)
        if case_type != "gate_pass":
            roi_img = capture_roi_image(page)
            cv2.imwrite(os.path.join(dir_evidence, f"{base_name}_p{page_num+1}_drawing_no.jpg"), roi_img, jpeg_opts)
            drawing_no = extract_drawing_no_tier1(page)
            if not drawing_no:
                tasks.append({"type": "drawing_no", "img": roi_img, "label": "Đọc Số Bản Vẽ"})

        # 2. Lưu duy nhất 1 ảnh bằng chứng Bảng khối lượng gốc (~150KB)
        for tbl_idx, table_img in enumerate(table_imgs):
            cv2.imwrite(os.path.join(dir_evidence, f"{base_name}_p{page_num+1}_table{tbl_idx+1}_{case_type}.jpg"), table_img, jpeg_opts)

            # Cắt khúc CHỈ TRÊN RAM - KHÔNG GHI Ổ CỨNG
            h = table_img.shape[0]
            if h > config.MAX_CHUNK_HEIGHT:
                cut_points = get_smart_cut_points_case1(table_img, config.MAX_CHUNK_HEIGHT) if case_type == "case1" else get_smart_cut_points_case2(table_img, config.MAX_CHUNK_HEIGHT)
                for i in range(len(cut_points) - 1):
                    img_chunk = table_img[cut_points[i]:cut_points[i+1], :]
                    if np.std(img_chunk) < 5: continue
                    tasks.append({"type": "table", "case_type": case_type, "img": img_chunk, "label": f"Bảng {tbl_idx+1} - Khúc {i+1}"})
            else:
                tasks.append({"type": "table", "case_type": case_type, "img": table_img, "label": f"Bảng {tbl_idx+1} - Toàn Bộ"})

        # 3. Bắn đa luồng lên AI Server
        dfs_to_combine = []
        if tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_AI_WORKERS) as executor:
                future_to_task = {executor.submit(call_ai_vision, task): task for task in tasks}
                for future in concurrent.futures.as_completed(future_to_task):
                    task_info = future_to_task[future]
                    try:
                        res = future.result()
                        if res["type"] == "drawing_no" and res["data"]: drawing_no = res["data"]
                        elif res["type"] == "table" and not res["data"].empty: dfs_to_combine.append((task_info["label"], res["data"]))
                    except Exception as e:
                        print(f"❌ {task_info['label']} lỗi: {e}")

        # 4. Gộp dòng và lưu CSV
        if dfs_to_combine:
            dfs_to_combine.sort(key=lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x[0])])
            final_df = pd.concat([df for _, df in dfs_to_combine], ignore_index=True)
            final_df = final_df.replace(r'^\s*$', pd.NA, regex=True).dropna(how='all')

            if case_type == "gate_pass":
                final_df.to_csv(os.path.join(dir_csv_gatepass, f"GATEPASS_{base_name}_p{page_num+1}.csv"), index=False, encoding='utf-8-sig')
            else:
                dwg = re.sub(r'[\\/*?:"<>|]', "", str(drawing_no)).strip() if drawing_no else f"{base_name}_p{page_num+1}"
                final_df = final_df.drop_duplicates(subset=["SDAC_CODE", "QTY", "PHU_TROI", "REMARK"], keep='first')
                final_df.to_csv(os.path.join(dir_csv_drawings, f"{dwg}.csv"), index=False, encoding='utf-8-sig')


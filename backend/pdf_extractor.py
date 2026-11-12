import os
import re
import time
import json
import base64
import requests
import glob
import concurrent.futures

import fitz          # PyMuPDF
import cv2           # OpenCV
import numpy as np
import pandas as pd
import config
import utils as ut


def debug_show(img, title="Debug Window"):
    """Hàm hiển thị ảnh debug cho phép co giãn chuột, không bị tràn màn hình."""
    # if img is None:
    #     print(f"⚠️ Ảnh '{title}' rỗng (None)!")
    #     return
    # cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    # cv2.resizeWindow(title, 1000, 700)
    # cv2.imshow(title, img)
    # print(f"👉 Đang hiển thị: [{title}]. Bấm phím bất kỳ trên bàn phím để tiếp tục...")
    # cv2.waitKey(0)
    # cv2.destroyWindow(title)
    return


def debug_show_all(image_dict):
    """Hiển thị tất cả ảnh trong Dictionary cùng một lúc lên các cửa sổ khác nhau."""
    # if not image_dict: return
    # for title, img in image_dict.items():
    #     if img is None: continue
    #     cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    #     cv2.resizeWindow(title, 600, 600)
    #     cv2.imshow(title, img)
    # print("👉 [DEBUG] Đã mở tất cả cửa sổ. Bấm phím SPACE để tiếp tục...")
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    return


# ==========================================
# KHỐI LOGIC 1: TRÍCH XUẤT CASE 1 (ẢNH NHÚNG OLE - HYBRID FAST MODE)
# ==========================================
def _score_horizontal_lines(img):
    """Hàm phụ trợ: Chấm điểm mật độ đường kẻ ngang để xác nhận ảnh là Bảng."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        ~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    horizontal_lines = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel)
    return np.sum(horizontal_lines > 0)


def _render_bbox_to_cv2(page, rect, dpi=250):
    """Hàm phụ trợ: Cắt và render một vùng Rect trên PDF sang ảnh OpenCV BGR."""
    pix = page.get_pixmap(clip=rect, dpi=dpi)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def extract_table_from_embedded_image(doc, page):
    """
    Trích xuất bảng Excel dán dạng OLE vào CAD (Case 1).
    (UPDATE): Trả về list ảnh thay vì 1 ảnh.
    """
    image_info_list = page.get_image_info(xrefs=True)
    if not image_info_list:
        return []

    page_area = page.rect.width * page.rect.height
    use_fast_mode = getattr(config, 'OLE_FAST_MODE', True)

    # 🚀 NHÁNH 1: FAST-MODE (Kiểm tra trực tiếp image_info_list[1])
    if use_fast_mode and len(image_info_list) >= 2:
        bbox = image_info_list[1]["bbox"]
        rect = fitz.Rect(bbox)
        if rect.width >= 50 and rect.height >= 50 and (rect.width * rect.height) / page_area <= 0.8:
            img_fast = _render_bbox_to_cv2(page, rect, dpi=250)
            if _score_horizontal_lines(img_fast) >= 1000:
                print(
                    "   ✅ Kích hoạt Case 1 (Fast-Mode image[1]): Đã bắt được bảng OLE!")
                return [img_fast]

    # 🛡️ NHÁNH 2: FALLBACK QUÉT TOÀN BỘ ẢNH NHÚNG
    best_img = None
    max_line_score = 0

    for img_info in image_info_list:
        bbox = img_info["bbox"]
        if bbox[2] - bbox[0] < 50 or bbox[3] - bbox[1] < 50:
            continue

        rect = fitz.Rect(bbox)
        if (rect.width * rect.height) / page_area > 0.8:
            continue

        img = _render_bbox_to_cv2(page, rect, dpi=250)
        score = _score_horizontal_lines(img)

        if score > max_line_score:
            max_line_score = score
            best_img = img

    if max_line_score >= 1000 and best_img is not None:
        print("   ✅ Kích hoạt Case 1 (Scan-Mode): Đã bắt được bảng OLE!")
        return [best_img]

    return []


# ==========================================
# KHỐI LOGIC 2: TRÍCH XUẤT CASE 2 & GATE PASS (MAGIC CROP)
# ==========================================
def extract_table_native_cad(doc, page, is_gate_pass=False):
    """
    (UPDATE): Tìm tất cả Mỏ neo (Multi-Anchor) để xuất ra nhiều bảng.
    Giữ lại toàn bộ hệ thống debug_images của phiên bản gốc.
    """
    if is_gate_pass:
        anchor_keywords = ["Item code", "Tên Vật Tư", "Số Lượng", "Tình Trạng"]
    else:
        anchor_keywords = ["Specification", "Q'TY",
                           "Item Code", "Item code", "Phụ trội", "Remark"]

    dpi = 200
    pix = page.get_pixmap(dpi=dpi)
    scale_x = pix.width / page.rect.width
    scale_y = pix.height / page.rect.height

    anchor_centers = []
    for kw in anchor_keywords:
        text_instances = page.search_for(kw)
        if text_instances:
            print(
                f"      📍 Đã bắt được {len(text_instances)} Mỏ neo Text: '{kw}'")
            for rect in text_instances:
                cx = (rect.x0 + rect.x1) / 2 * scale_x
                cy = (rect.y0 + rect.y1) / 2 * scale_y
                anchor_centers.append((cx, cy))

    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    img = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(
        img_np, cv2.COLOR_RGB2BGR)
    h_img, w_img = img.shape[:2]

    # KHỞI TẠO BỘ DEBUG Y HỆT BẢN GỐC
    debug_images = {}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug_images["NativeCad 0. Anh Gray"] = gray
    thresh = cv2.adaptiveThreshold(
        ~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    debug_images["NativeCad 1. Anh X-Quang"] = thresh
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (150, 1))
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
    debug_images["NativeCad 2. Net Ngang"] = h_lines

    # Xóa viền khung bao ngoài trang giấy
    contours_h, _ = cv2.findContours(
        h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_h:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > w_img * 0.85:
            cv2.drawContours(h_lines, [cnt], -1, 0, -1)

    debug_images["NativeCad 3. Loc Net Ngang (Chi con duong ke ngang)"] = h_lines

    fuse_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 80))
    table_mask = cv2.dilate(h_lines, fuse_kernel, iterations=1)
    debug_images["NativeCad 4. Khuon Dilate"] = table_mask

    contours, _ = cv2.findContours(
        table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    valid_bboxes = []

    if anchor_centers:
        for ax, ay in anchor_centers:
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w < 300 or h < 50:
                    continue
                if (x - 80 <= ax <= x + w + 80) and (y - 80 <= ay <= y + h + 80):
                    valid_bboxes.append(
                        {"bbox": (x, y, w, h), "anchor": (ax, ay)})
                    break
    else:
        max_area = 0
        best_bbox = None
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w >= 300 and h >= 50 and w * h > max_area:
                max_area = w * h
                best_bbox = (x, y, w, h)
        if best_bbox:
            valid_bboxes.append({"bbox": best_bbox, "anchor": None})

    # Lọc các bảng trùng lặp (nếu nhiều mỏ neo cùng trỏ vào 1 bảng)
    unique_bboxes = []
    seen_rects = set()
    for item in valid_bboxes:
        rect = item["bbox"]
        if rect not in seen_rects:
            seen_rects.add(rect)
            unique_bboxes.append(item)

    if not unique_bboxes:
        return []

    extracted_tables = []

    # XỬ LÝ MAGIC CROP CHO TỪNG BẢNG
    for idx, item in enumerate(unique_bboxes):
        x, y, w, h = item["bbox"]
        anchor_center = item["anchor"]

        # ✂️ THUẬT TOÁN MAGIC CROP (Giữ nguyên logic kiểm tra anchor_center gốc)
        shave = 15
        if h > shave * 3:
            roi_h_internal = h_lines[y+shave: y+h-shave, x:x+w]
            h_cnts, _ = cv2.findContours(
                roi_h_internal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            start_xs = [cv2.boundingRect(
                c)[0] for c in h_cnts if cv2.boundingRect(c)[2] > 150]
            end_xs = [cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2]
                      for c in h_cnts if cv2.boundingRect(c)[2] > 150]

            def get_consensus(values, tolerance=20):
                if not values:
                    return None
                max_count = 0
                best_val = None
                for v in values:
                    count = sum(1 for other in values if abs(
                        v - other) <= tolerance)
                    if count > max_count:
                        max_count = count
                        best_val = v
                return best_val

            true_sx = get_consensus(start_xs)
            true_ex = get_consensus(end_xs)

            if true_sx is not None and true_ex is not None:
                new_w = true_ex - true_sx
                if new_w > 300:
                    if anchor_center:
                        ax_global = anchor_center[0]
                        new_x_global = x + true_sx
                        new_ex_global = x + true_ex
                        if (new_x_global - 50 <= ax_global <= new_ex_global + 50):
                            print(
                                f"      ✂️ Magic Crop: Đã gọt sạch {true_sx}px viền rác thừa!")
                            x, w = new_x_global, new_w
                    else:
                        x, w = x + true_sx, new_w

        pad = 20
        x_crop, y_crop = max(0, x - pad), max(0, y - pad)
        w_crop, h_crop = min(
            img.shape[1] - x_crop, w + 2 * pad), min(img.shape[0] - y_crop, h + 2 * pad)

        final_crop = img[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop]
        debug_images[f"NativeCad 5. Thanh qua sau Magic Crop (Bang {idx+1})"] = final_crop
        extracted_tables.append(final_crop)

    debug_show_all(debug_images)

    label_mode = "Gate Pass PDF" if is_gate_pass else "Case 2 (Native CAD)"
    print(
        f"   ✅ Kích hoạt {label_mode}: Bắt thành công {len(extracted_tables)} Bảng!")
    return extracted_tables


# ==========================================
# TRẠM ĐIỀU PHỐI (MASTER DISPATCHER)
# ==========================================
def is_gate_pass_page(page, force_mode=None):
    """Kiểm tra xem trang PDF hiện tại có phải là Biên bản vật tư mang vào (Gate Pass) không."""
    if force_mode == "gate_pass":
        return True
    if force_mode == "drawing":
        return False

    page_text = page.get_text("text").upper()
    gp_markers = [
        "VẬT TƯ MANG VÀO",
        "THÔNG TIN CHI TIẾT HÀNG MANG VÀO",
        "TÊN VẬT TƯ",
        "TÊN THÔNG THƯỜNG"
    ]
    return any(marker in page_text for marker in gp_markers)


def get_table_image_from_page(doc, page, force_mode=None):
    """
    Hàm Trạm trưởng: Trả về Danh sách ảnh Bảng và Nhãn luồng xử lý.
    """
    print("   🔍 Đang quét Radar phân tích cấu trúc PDF...")

    if is_gate_pass_page(page, force_mode):
        print("   🏷️ Phát hiện form 'Thông tin vật tư mang vào' (Gate Pass) -> Chuyển thẳng sang Magic Crop!")
        imgs_gp = extract_table_native_cad(doc, page, is_gate_pass=True)
        if imgs_gp:
            return imgs_gp, "gate_pass"
        return [], None

    imgs_case1 = extract_table_from_embedded_image(doc, page)
    if imgs_case1:
        return imgs_case1, "case1"

    print("      ⚠️ Không phát hiện khối ảnh OLE hợp lệ. Chuyển hướng dò quét Native CAD...")
    imgs_case2 = extract_table_native_cad(doc, page, is_gate_pass=False)
    if imgs_case2:
        return imgs_case2, "case2"

    print("      ❌ Không tìm thấy vùng Bảng nào phù hợp.")
    return [], None


# ==========================================
# BƯỚC 1.5 - ĐỌC SỐ BẢN VẼ (CHỈ DÙNG CHO BẢN VẼ CAD)
# ==========================================
def capture_roi_image(page):
    rect = page.rect
    roi = config.ROI_DRAWING_NO
    clip_rect = fitz.Rect(
        rect.width * roi[0], rect.height * roi[1], rect.width * roi[2], rect.height * roi[3])
    pix = page.get_pixmap(clip=clip_rect, dpi=150)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def extract_drawing_no_tier1(page):
    rect = page.rect
    roi = config.ROI_DRAWING_NO
    clip_rect = fitz.Rect(
        rect.width * roi[0], rect.height * roi[1], rect.width * roi[2], rect.height * roi[3])
    text = page.get_text("text", clip=clip_rect)

    if text.strip():
        print(
            f"   [Debug] Text dò được ở vùng ROI:\n   >>> {repr(text.strip())}")

    match = re.search(r"DRAWING\s*NO\.?([\s\S]+)", text, re.IGNORECASE) or re.search(
        r"BẢN\s*VẼ([\s\S]+)", text, re.IGNORECASE)
    if match:
        for line in match.group(1).split('\n'):
            line = line.strip()
            if line and not re.match(r'^(?:A[0-4]|TỶ|SCALE)', line, re.IGNORECASE):
                clean_no = re.sub(r'[^\w\-]', '', line)
                if clean_no and clean_no.upper() not in ["DRAWING", "NO"]:
                    return clean_no
    return None


# ==========================================
# BƯỚC 2 - MÀNG LỌC ẢO GIÁC & GỌI AI VISION
# ==========================================
def encode_image(img):
    h, w = img.shape[:2]
    scale = config.TARGET_IMG_HEIGHT / h if h > 0 else 1
    new_w, new_h = int(w * scale), int(h * scale)
    if new_w > config.MAX_IMG_WIDTH:
        scale = config.MAX_IMG_WIDTH / w
        new_w, new_h = int(w * scale), int(h * scale)
    img_resized = cv2.resize(
        img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    _, buffer = cv2.imencode('.jpg', img_resized, [int(
        cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY])
    return base64.b64encode(buffer).decode('utf-8')


def clean_ai_dataframe(df):
    if df.empty:
        return df
    df_clean = df.copy()
    if 'SDAC_CODE' in df_clean.columns:
        df_clean['SDAC_CODE'] = df_clean['SDAC_CODE'].astype(
            str).str.strip().str.upper()
        df_clean = df_clean[df_clean['SDAC_CODE'].str.len() > 5]
        df_clean = df_clean[df_clean['SDAC_CODE'].str.contains(
            r'-', regex=True)]
    return df_clean


def call_ai_vision(task_data):
    task_type = task_data["type"]
    case_type = task_data.get("case_type", "case1")
    img = task_data["img"]
    label = task_data["label"]
    print(f"-> Đang gửi [{label}] ({case_type}) lên AI...")
    base64_image = encode_image(img)

    if task_type == "drawing_no":
        prompt = (
            "Đây là khu vực 'SỐ BẢN VẼ - DRAWING NO' ở góc bản vẽ. "
            "Hãy đọc và trả về DUY NHẤT mã số/chuỗi ký tự của bản vẽ đó (Ví dụ: 1, 2, 3, A-01). "
            "Tuyệt đối không giải thích hay thêm chữ nào khác."
        )
    elif case_type == "gate_pass":
        prompt = """
        Bạn là chuyên gia kiểm soát vật tư MEP.
        Đây là bảng "THÔNG TIN VẬT TƯ MANG VÀO NHÀ MÁY" gồm các cột theo thứ tự:
        STT -> Item code -> Tên Vật Tư -> Thông Số Kỹ Thuật -> Tên thông thường -> Số Lượng -> Đơn Vị Tính -> Tình Trạng -> Hình Ảnh -> Ghi Chú.

        Hãy quét từng dòng và trích xuất ra mảng JSON chỉ gồm 2 key sau:
        1. "SDAC_CODE": Lấy ở cột "Item code". Mã LUÔN LUÔN có đúng 12 ký tự (Ví dụ: M03-00726974).
        2. "QTY": Lấy con số ở cột "Số Lượng" (nằm ngay bên trái cột Đơn Vị Tính).
        LƯU Ý QUAN TRỌNG (ZERO HALLUCINATION):
        - Phớt lờ hoàn toàn cột Hình Ảnh. Chỉ trả về JSON hợp lệ. Nếu mảnh ảnh chỉ có chữ ký hoặc khoảng trắng, trả về [].
        """
    else:
        # 🌟 (UPDATE V1.1): PROMPT MỚI, CHỐNG NHIỄU CỘT
        prompt = """
        Bạn là chuyên gia bóc tách khối lượng MEP. Các cột trong bảng có thể không cố định thứ tự và chứa nhiều cột phụ (From, To, Calculator...).
        Hãy phớt lờ mọi cột phụ, dùng khả năng suy luận để ĐỊNH VỊ CHÍNH XÁC 4 giá trị sau dựa vào tiêu đề cột:
       
        1. "SDAC_CODE": Nằm dưới cột Item code / Code.
            - Mã LUÔN LUÔN CÓ ĐÚNG 12 KÝ TỰ (Ví dụ: M03-21668484). Chữ + 2 chữ số + Dấu gạch "-" + 8 chữ số.
            - BẮT BUỘC BẠN PHẢI ĐẾM LẠI : Nếu AI đọc ra 11 ký tự -> Bị dính nét, hãy nhìn kỹ lại để tách ra cho đủ 12.
            - BẮT BUỘC BẠN PHẢI ĐẾM LẠI : Nếu AI đọc ra 13 ký tự -> Nhìn nhầm nét thừa, hãy đếm và cắt bỏ số rác để còn đúng 12.
            - ĐẶC BIỆT CHÚ Ý: Do nét vẽ CAD bị nhiễu, bạn rất dễ bị ảo giác nhìn 1 số thành 2 số (Ví dụ: 88 thành 888, 6 thành 66).
        2. "QTY": Nằm dưới cột có tiêu đề Q'TY hoặc Số Lượng. Đây là con số KHỐI LƯỢNG TỔNG CHỐT HẠ của dòng đó, KHÔNG bốc số ở các cột phụ kiện như Calculator, From, To.
        3. "PHU_TROI": Nằm dưới tiêu đề Phụ Trội (chứa % như 20%, 30% hoặc ký hiệu phân loại CR-A, CR-B). Nếu ô trống để "".
        4. "REMARK": Chứa chữ "SDV" hoặc ô trống. TUYỆT ĐỐI CHỈ NHẬN CHỮ "SDV" hoặc để rỗng "".

        Chỉ trả về JSON.
        LƯU Ý CỰC KỲ QUAN TRỌNG (ZERO HALLUCINATION):
        1. CHỈ TRÍCH XUẤT những gì thực sự nhìn thấy rõ ràng trong ảnh. Cố tình lọc bỏ các Note ghi chú viết tay đè lên bản vẽ.
        2. Nếu bức ảnh là khoảng trắng, đường kẻ rỗng, hoặc không chứa mã hợp lệ, PHẢI TRẢ VỀ [].
        """

    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}", "detail": "high"}}
                ]
            }
        ],
        "temperature": config.TEMPERATURE
    }
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {config.API_KEY}"}

    for attempt in range(config.MAX_RETRIES):
        try:
            response = requests.post(
                config.API_URL, headers=headers, json=payload, timeout=120, proxies={"http": None, "https": None}
            )
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content'].replace(
                "```json", "").replace("```", "").strip()

            if task_type == "drawing_no":
                return {"type": "drawing_no", "data": result_text}

            start_idx = min([i for i in [result_text.find(
                '['), result_text.find('{')] if i >= 0] or [0])
            parsed_json, _ = json.JSONDecoder().raw_decode(
                result_text[start_idx:])

            if isinstance(parsed_json, dict):
                list_found = False
                for k, v in parsed_json.items():
                    if isinstance(v, list):
                        parsed_json = v
                        list_found = True
                        break
                if not list_found:
                    parsed_json = [parsed_json] if parsed_json else []
            elif not isinstance(parsed_json, list):
                parsed_json = []

            df = pd.DataFrame(parsed_json)
            if not df.empty:
                if 'QTY' in df.columns:
                    # Xử lý trường hợp AI đọc số có dấu phẩy ngăn cách hàng nghìn
                    df['QTY'] = df['QTY'].astype(
                        str).str.replace(',', '').str.strip()
                    df['QTY'] = pd.to_numeric(
                        df['QTY'], errors='coerce').fillna(0)

                if case_type == "gate_pass":
                    df = df.reindex(columns=["SDAC_CODE", "QTY"]).fillna(
                        {"SDAC_CODE": "", "QTY": 0})
                else:
                    if 'REMARK' in df.columns:
                        df['REMARK'] = df['REMARK'].apply(
                            lambda x: "SDV" if "SDV" in str(x).upper() else "")
                    df = df.reindex(
                        columns=["SDAC_CODE", "QTY", "PHU_TROI", "REMARK"]).fillna("")

                df = clean_ai_dataframe(df)

            return {"type": "table", "data": df}

        except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return {"type": task_type, "data": "" if task_type == "drawing_no" else pd.DataFrame()}
    return {"type": task_type, "data": "" if task_type == "drawing_no" else pd.DataFrame()}


# ==========================================
# BƯỚC 3 - CÁC DAO CẮT CHUNK (DUAL-ROUTING)
# ==========================================
def get_smart_cut_points_case1(img, max_chunk_height):
    """Dao cắt Case 1 (Cắt theo đường kẻ ngang OpenCV V2)."""
    debug_images = {}
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug_images["Cut Case1 : 0. Anh Gray"] = gray
    thresh = cv2.adaptiveThreshold(
        ~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    debug_images["Cut Case1 : 1. Anh X-Quang"] = thresh
    kernel_len = max(100, w // 4)
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (kernel_len, 1))
    horizontal_lines = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel)
    debug_images["Cut Case1 : 2. Loc Net Ngang (Chi con duong ke ngang)"] = horizontal_lines
    row_sums = np.sum(horizontal_lines, axis=1)
    line_y_coords = np.where(row_sums > 0)[0]

    cut_points, current_y = [0], 0
    while current_y + max_chunk_height < h:
        target_y = current_y + max_chunk_height
        valid_lines = line_y_coords[(
            line_y_coords >= target_y - 60) & (line_y_coords <= target_y + 60)]
        if len(valid_lines) > 0:
            best_y = valid_lines[np.argmin(np.abs(valid_lines - target_y))]
            cut_points.append(best_y)
            current_y = best_y
        else:
            cut_points.append(target_y)
            current_y = target_y
    cut_points.append(h)

    debug_img = img.copy()
    for y_cut in cut_points:
        # Lệnh vẽ đường thẳng màu Xanh lá (0, 255, 0) đè lên đường kẻ ngang của Excel
        cv2.line(debug_img, (0, y_cut), (w, y_cut), (0, 255, 0), 2)

    debug_images["Cut Case1 : 3. Vet Dao Chem (Case 1 - Cat Tren Duong Ke"] = debug_img
    debug_show_all(debug_images)

    return cut_points


def get_smart_cut_points_case2(img, max_chunk_height):
    """Dao cắt Case 2 & Gate Pass (Cắt luồn lách qua khe hẹp/khoảng trắng chữ V3)."""
    debug_images = {}
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug_images["Cut Case2 : 0. Anh Gray"] = gray
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    debug_images["Cut Case2 : 1. Anh X-Quang"] = thresh
    thresh_dilated = cv2.dilate(thresh, cv2.getStructuringElement(
        cv2.MORPH_RECT, (15, 5)), iterations=1)
    debug_images["Cut Case2 : 2. Anh thresh_dilated"] = thresh_dilated
    row_sums = np.sum(thresh_dilated, axis=1)

    cut_points, current_y = [0], 0
    while current_y + max_chunk_height < h:
        target_y = current_y + max_chunk_height
        search_min = max(current_y + 50, target_y - 80)
        best_y, min_pixels = target_y, float('inf')

        for y in range(target_y, search_min, -1):
            if row_sums[y] < min_pixels:
                min_pixels = row_sums[y]
                best_y = y
                if min_pixels == 0:
                    break

        cut_points.append(best_y)
        current_y = best_y
    cut_points.append(h)

    debug_img = img.copy()
    # Vòng lặp vẽ các vạch đỏ (chính là vết dao chém)
    for y_cut in cut_points:
        # Lệnh vẽ đường thẳng màu Đỏ (0, 0, 255), dày 2px vắt ngang qua ảnh
        cv2.line(debug_img, (0, y_cut), (w, y_cut), (0, 0, 255), 2)

    # Xem tận mắt lưỡi dao lách qua các dòng chữ như thế nào
    debug_images["Cut Case2 : 3. Vet Dao Chem (Case 2 - Tim Khe Ho)"] = debug_img
    debug_show_all(debug_images)

    return cut_points


# ==========================================
# HÀM XỬ LÝ CHÍNH (HỖ TRỢ GỌI TỪ CLI HOẶC WEB SERVER)
# ==========================================
def process_single_pdf(pdf_path, force_mode=None, out_drawing_dir=None, out_gatepass_dir=None, out_img_dir=None):
    """
    Xử lý 1 file PDF bất kỳ (Bản vẽ hoặc Gate Pass).
    """
    file_name = os.path.basename(pdf_path)
    print(f"\n{'='*50}\n⚙ BẮT ĐẦU XỬ LÝ FILE: {file_name}\n{'='*50}")
    start_time = time.time()
    doc = fitz.open(pdf_path)
    base_name = ut.clean_vietnamese_filename(os.path.splitext(file_name)[0])

    dir_csv_drawings = out_drawing_dir or config.DIR_CSV_EXTRACTED
    dir_csv_gatepass = out_gatepass_dir or getattr(
        config, 'DIR_GATEPASS_CSV', config.DIR_CSV_EXTRACTED)
    dir_img_extracted = out_img_dir or config.DIR_IMG_EXTRACTED
    os.makedirs(dir_csv_drawings, exist_ok=True)
    os.makedirs(dir_csv_gatepass, exist_ok=True)
    os.makedirs(dir_img_extracted, exist_ok=True)

    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"\n📄 Đang quét Trang {page_num + 1}/{len(doc)}...")

        # 0. Render ảnh toàn trang bản vẽ phục vụ xem chi tiết trên Lightbox UI
        try:
            page_pix = page.get_pixmap(dpi=150)
            page_img_path = os.path.join(
                dir_img_extracted, f"{base_name}_page{page_num+1}_drawing_preview.png")
            page_pix.save(page_img_path)
        except Exception:
            pass

        # 1. Trạm điều phối trả về DANH SÁCH ẢNH BẢNG
        table_imgs, case_type = get_table_image_from_page(
            doc, page, force_mode=force_mode)
        if not table_imgs:
            print("-> ⏭️ Trang này không chứa Bảng hợp lệ. Bỏ qua.")
            continue

        tasks = []
        drawing_no = None

        if case_type != "gate_pass":
            roi_img = capture_roi_image(page)
            cv2.imwrite(os.path.join(dir_img_extracted,
                        f"{base_name}_page{page_num+1}_roi_debug.png"), roi_img)
            drawing_no = extract_drawing_no_tier1(page)
            if not drawing_no:
                print(
                    "-> ⚠️ Tầng 1 không dò được Số Bản Vẽ. Kích hoạt AI Vision đọc ảnh ROI...")
                tasks.append(
                    {"type": "drawing_no", "img": roi_img, "label": "Đọc Số Bản Vẽ"})
            else:
                print(f"-> ✅ Chốt Số Bản Vẽ (Tầng 1): '{drawing_no}'")

        # 2. VÒNG LẶP XỬ LÝ NHIỀU BẢNG (MULTI-TABLE CHUNKING)
        for tbl_idx, table_img in enumerate(table_imgs):
            h, w = table_img.shape[:2]
            cv2.imwrite(os.path.join(dir_img_extracted,
                        f"{base_name}_page{page_num+1}_table{tbl_idx+1}_{case_type}.png"), table_img)

            if h > config.MAX_CHUNK_HEIGHT:
                if case_type == "case1":
                    cut_points = get_smart_cut_points_case1(
                        table_img, config.MAX_CHUNK_HEIGHT)
                else:
                    cut_points = get_smart_cut_points_case2(
                        table_img, config.MAX_CHUNK_HEIGHT)

                for i in range(len(cut_points) - 1):
                    y_start, y_end = cut_points[i], cut_points[i+1]
                    img_chunk = table_img[y_start:y_end, :]
                    if np.std(img_chunk) < 5:
                        continue

                    cv2.imwrite(os.path.join(
                        dir_img_extracted, f"{base_name}_page{page_num+1}_table{tbl_idx+1}_chunk_{i+1}.png"), img_chunk)
                    tasks.append({"type": "table", "case_type": case_type,
                                 "img": img_chunk, "label": f"Bảng {tbl_idx+1} - Khúc {i+1}"})
            else:
                tasks.append({"type": "table", "case_type": case_type,
                             "img": table_img, "label": f"Bảng {tbl_idx+1} - Toàn Bộ"})

        # 3. Bắn Đa luồng lên AI Server
        dfs_to_combine = []
        if tasks:
            print(
                f"-> 🚀 Bắn Đa luồng ({len(tasks)} nhiệm vụ) lên AI Server...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_AI_WORKERS) as executor:
                future_to_task = {executor.submit(
                    call_ai_vision, task): task for task in tasks}
                for future in concurrent.futures.as_completed(future_to_task):
                    task_info = future_to_task[future]
                    try:
                        res = future.result()
                        if res["type"] == "drawing_no" and res["data"]:
                            drawing_no = res["data"]
                            print(
                                f"-> ✅ AI đã đọc được Số Bản Vẽ (Tầng 2): '{drawing_no}'")
                        elif res["type"] == "table" and not res["data"].empty:
                            dfs_to_combine.append(
                                (task_info["label"], res["data"]))
                    except Exception as e:
                        print(f"❌ {task_info['label']} bị lỗi: {e}")

        # 4. Lưu kết quả ra CSV
        if dfs_to_combine:
            # Sắp xếp đúng thứ tự: Bảng 1 Khúc 1 -> Bảng 1 Khúc 2 -> Bảng 2 Khúc 1
            dfs_to_combine.sort(
                key=lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x[0])])
            final_df = pd.concat(
                [df for _, df in dfs_to_combine], ignore_index=True)
            final_df = final_df.replace(
                r'^\s*$', pd.NA, regex=True).dropna(how='all')

            if case_type == "gate_pass":
                out_name = f"GATEPASS_{base_name}_p{page_num+1}.csv"
                out_path = os.path.join(dir_csv_gatepass, out_name)
                final_df.to_csv(out_path, index=False, encoding='utf-8-sig')
                print(
                    f"🎉 [Gate Pass] Bóc tách thành công -> Lưu CSV: '{out_name}'")
            else:
                if not drawing_no:
                    drawing_no = f"{base_name}_p{page_num+1}"
                else:
                    drawing_no = re.sub(
                        r'[\\/*?:"<>|]', "", str(drawing_no)).strip()

                final_df = final_df.drop_duplicates(
                    subset=["SDAC_CODE", "QTY", "PHU_TROI", "REMARK"], keep='first')
                out_name = f"{drawing_no}.csv"
                out_path = os.path.join(dir_csv_drawings, out_name)
                final_df.to_csv(out_path, index=False, encoding='utf-8-sig')
                print(
                    f"🎉 [Bản Vẽ] Bóc tách thành công {len(table_imgs)} Bảng -> Lưu chung vào 1 CSV: '{out_name}'")
        else:
            print("⚠️ Không bóc tách được dữ liệu bảng nào ở trang này.")

    print(
        f"⏱️ HOÀN TẤT FILE {file_name} (Thời gian: {time.time() - start_time:.2f}s)")


def run_extraction_pipeline():
    """Hàm gom toàn bộ PDF từ các thư mục cấu hình và chạy trích xuất."""
    total_start = time.time()
    tasks_queue = []

    if hasattr(config, 'DIR_PDF_DRAWINGS') and os.path.exists(config.DIR_PDF_DRAWINGS):
        for p in glob.glob(os.path.join(config.DIR_PDF_DRAWINGS, "*.pdf")):
            tasks_queue.append((p, "drawing"))

    if hasattr(config, 'DIR_PDF_GATEPASS') and os.path.exists(config.DIR_PDF_GATEPASS):
        for p in glob.glob(os.path.join(config.DIR_PDF_GATEPASS, "*.pdf")):
            tasks_queue.append((p, "gate_pass"))

    if hasattr(config, 'DIR_PDF_INPUT') and os.path.exists(config.DIR_PDF_INPUT):
        for p in glob.glob(os.path.join(config.DIR_PDF_INPUT, "*.pdf")):
            tasks_queue.append((p, None))  # None = Tự động phân loại bằng Text

    if not tasks_queue:
        print("⚠️ Không tìm thấy file PDF nào trong các thư mục Input!")
        return

    print(
        f"🚀 Tìm thấy {len(tasks_queue)} file PDF. Bắt đầu quy trình bóc tách...\n")
    for pdf_path, mode in tasks_queue:
        process_single_pdf(pdf_path, force_mode=mode)

    print(
        f"\n🏁 XONG TOÀN BỘ BƯỚC BÓC TÁCH PDF! Tổng thời gian: {(time.time() - total_start):.2f} giây")


if __name__ == "__main__":
    run_extraction_pipeline()

"""Đọc bảng vật tư trong ảnh bằng AI vision (API OpenAI-compatible: vLLM, Ollama, ...).
Chế độ thử: đọc lớp chữ trong PDF, không gọi AI.
"""
import base64
import json
import re
import time
import urllib.error
import urllib.request

from .compare import num
from .render import pdf_text_lines


def prompt(st):
    hint = f"Lưu ý thêm: {st['hint']}\n" if st.get("hint") else ""
    return f"""Bạn là chuyên viên kiểm tra BOM (danh sách vật tư) trong nhà máy. Ảnh là 1 trang bản vẽ/bảng vật tư.
Nhiệm vụ: đọc CHÍNH XÁC từng dòng trong bảng vật tư và số bản vẽ tương ứng.
- Số bản vẽ thường ở khung tên (title block) hoặc tiêu đề bảng. Nếu bảng có cột "số bản vẽ" cho từng dòng thì nhóm theo cột đó.
- Chép mã vật tư đúng từng ký tự, KHÔNG đoán, KHÔNG sửa. Ký tự nào không đọc rõ thì thay bằng "?".
- qty là số lượng dạng số; không có thì null.
- Nếu trang không có bảng vật tư, trả về {{"drawings":[]}}.
{hint}Chỉ trả về JSON, không giải thích, đúng mẫu:
{{"drawings":[{{"drawing_no":"...","items":[{{"code":"...","name":"...","qty":1}}]}}]}}"""


def parse_json(t: str):
    t = re.sub(r"<think>[\s\S]*?</think>", "", t or "")
    t = re.sub(r"```(json)?", "", t, flags=re.I)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("AI không trả về JSON")
    return json.loads(t[a:b + 1])


def call_ai(st, content, max_tokens):
    if not st.get("model"):
        raise RuntimeError("Chưa nhập tên model trong Cài đặt")
    body = json.dumps({"model": st["model"], "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": content}]}).encode()
    headers = {"Content-Type": "application/json"}
    if st.get("api_key"):
        headers["Authorization"] = "Bearer " + st["api_key"]
    req = urllib.request.Request(st["base_url"].rstrip("/") + "/chat/completions", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=st.get("timeout", 300)) as r:
            j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"AI lỗi HTTP {e.code}: {e.read()[:300].decode('utf-8', 'ignore')}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Không kết nối được AI ({st['base_url']}): {e.reason}")
    return ((j.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


def read_page(st, jpeg: bytes, idx: int, log):
    url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    content = [{"type": "text", "text": prompt(st)}, {"type": "image_url", "image_url": {"url": url}}]
    for attempt in (1, 2):
        try:
            j = parse_json(call_ai(st, content, st.get("max_tokens", 4096)))
            d = [{**x, "page": idx + 1} for x in j.get("drawings") or []]
            log(f"Trang {idx + 1}: {len(d)} bản vẽ, {sum(len(x.get('items') or []) for x in d)} dòng vật tư")
            return d
        except Exception as e:
            log(f"Trang {idx + 1} lần {attempt} lỗi: {e}")
            if attempt == 2:
                raise
            time.sleep(2)


RE_DWG = re.compile(r"DRAWING\s*NO\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9\-_./]*)", re.I)


def mock_read(pdf_list, log):
    out, page_no = [], 0
    for pdf in pdf_list:
        for lines in pdf_text_lines(pdf):
            page_no += 1
            dwg, items = "", []
            for cells in lines:
                m = RE_DWG.search(" ".join(cells))
                if m:
                    dwg = m.group(1)
                    continue
                if len(cells) >= 3 and cells[0].isdigit() and num(cells[-1]) is not None:
                    items.append({"code": cells[1], "name": " ".join(cells[2:-1]), "qty": num(cells[-1])})
            if not items and not dwg:
                log(f"Trang {page_no}: không có chữ (PDF dạng ảnh) – chế độ thử không đọc được, cần AI thật")
                continue
            log(f"Trang {page_no} [chế độ thử]: bản vẽ {dwg or '?'}, {len(items)} dòng vật tư")
            out.append({"drawing_no": dwg, "items": items, "page": page_no})
    return out
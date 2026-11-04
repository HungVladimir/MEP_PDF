"""PDF -> ảnh JPEG và PDF -> dòng chữ.

Ưu tiên PyMuPDF (pip install pymupdf). Không có thì dùng poppler-utils (pdftoppm, pdftotext).
"""
import glob
import io
import os
import re
import shutil
import subprocess
import tempfile

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


def _need_poppler(tool):
    if not shutil.which(tool):
        raise RuntimeError("Chưa cài PyMuPDF (pip install pymupdf) hoặc poppler-utils để đọc PDF")


def pdf_to_jpegs(pdf: bytes, max_side: int = 2000) -> list:
    if fitz:
        out = []
        with fitz.open(stream=pdf, filetype="pdf") as doc:
            for page in doc:
                r = page.rect
                scale = min(4.0, max_side / max(r.width, r.height))
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                out.append(pix.tobytes("jpeg", jpg_quality=90))
        return out
    _need_poppler("pdftoppm")
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "in.pdf")
        open(src, "wb").write(pdf)
        subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=90", "-scale-to", str(max_side), src, os.path.join(d, "p")],
                       check=True, capture_output=True, timeout=300)
        return [open(f, "rb").read() for f in sorted(glob.glob(os.path.join(d, "p-*.jpg")))]


def pdf_text_lines(pdf: bytes) -> list:
    """-> mỗi trang là danh sách dòng, mỗi dòng là danh sách ô chữ từ trái sang phải."""
    pages = []
    if fitz:
        with fitz.open(stream=pdf, filetype="pdf") as doc:
            for page in doc:
                lines = {}
                for b in page.get_text("dict")["blocks"]:
                    for ln in b.get("lines", []):
                        for sp in ln["spans"]:
                            t = sp["text"].strip()
                            if t:
                                y = round(sp["origin"][1] / 3)
                                lines.setdefault(y, []).append((sp["origin"][0], t))
                pages.append([[t for _, t in sorted(v)] for _, v in sorted(lines.items())])
        return pages
    _need_poppler("pdftotext")
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "in.pdf")
        open(src, "wb").write(pdf)
        txt = subprocess.run(["pdftotext", "-layout", src, "-"], check=True, capture_output=True, timeout=120).stdout.decode("utf-8", "ignore")
    for pg in txt.split("\f"):
        if pg.strip():
            pages.append([re.split(r"\s{2,}", ln.strip()) for ln in pg.splitlines() if ln.strip()])
    return pages


def image_size_ok(b: bytes) -> bool:
    return len(b) > 1000


def to_jpeg(b: bytes) -> bytes:
    """Ảnh PNG/JPG trong Excel -> JPEG (giữ nguyên nếu không có Pillow)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(b)).convert("RGB")
        o = io.BytesIO()
        im.save(o, "JPEG", quality=90)
        return o.getvalue()
    except Exception:
        return b
"""Tách PDF (hoặc ảnh) nhúng trong file Excel .xlsx/.xlsm.

PDF chèn bằng Insert > Object được lưu ở xl/embeddings/oleObjectN.bin (định dạng OLE Compound File).
Đọc đúng từng stream trong file OLE để PDF không bị đứt khi các sector nằm rời nhau.
"""
import struct
import zipfile

PDF_HEAD, PDF_EOF = b"%PDF-", b"%%EOF"
CFB_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
ENDS = 0xFFFFFFFA  # giá trị >= đây là sector đặc biệt (END/FREE/FAT/DIFAT)


def find_pdf(b: bytes):
    s = b.find(PDF_HEAD)
    if s < 0:
        return None
    e = b.rfind(PDF_EOF)
    return b[s:e + 5] if e > s else b[s:]


def cfb_streams(data: bytes):
    """Trả về danh sách (tên, nội dung) các stream trong file OLE. Lỗi định dạng -> []."""
    if data[:8] != CFB_SIG:
        return []
    try:
        ssz = 1 << struct.unpack_from("<H", data, 30)[0]
        mssz = 1 << struct.unpack_from("<H", data, 32)[0]
        (n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat, difat_start, n_difat) = struct.unpack_from("<8I", data, 44)
        sec = lambda i: data[(i + 1) * ssz:(i + 2) * ssz]
        per = ssz // 4

        difat = list(struct.unpack_from("<109I", data, 76))
        d, k = difat_start, 0
        while d < ENDS and k < n_difat:
            ent = struct.unpack(f"<{per}I", sec(d))
            difat += ent[:-1]
            d, k = ent[-1], k + 1
        fat = []
        for f in difat[:max(n_fat, 0) or len(difat)]:
            if f < ENDS:
                fat += struct.unpack(f"<{per}I", sec(f))

        def chain(start, table):
            seen = set()
            while start < ENDS and start < len(table) and start not in seen:
                seen.add(start)
                yield start
                start = table[start]

        read = lambda start, size=None: b"".join(sec(i) for i in chain(start, fat))[:size]

        dirs = read(dir_start)
        entries = []
        for off in range(0, len(dirs) - 127, 128):
            e = dirs[off:off + 128]
            nlen = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(nlen - 2, 0)].decode("utf-16-le", "ignore")
            typ = e[66]
            start, size = struct.unpack_from("<II", e, 116)
            entries.append((name, typ, start, size))
        if not entries:
            return []
        root = entries[0]
        mini_stream = read(root[2], root[3]) if root[2] < ENDS else b""
        minifat = []
        if n_minifat and minifat_start < ENDS:
            raw = read(minifat_start)
            minifat = list(struct.unpack(f"<{len(raw) // 4}I", raw[:len(raw) // 4 * 4]))

        out = []
        for name, typ, start, size in entries[1:]:
            if typ != 2 or size == 0:
                continue
            if size < mini_cutoff:
                b = b"".join(mini_stream[i * mssz:(i + 1) * mssz] for i in chain(start, minifat))[:size]
            else:
                b = read(start, size)
            out.append((name, b))
        return out
    except Exception:
        return []


def extract_from_xlsx(path: str, log=print):
    """-> (pdfs: [(tên, bytes)], images: [bytes])"""
    pdfs, images = [], []
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            low = name.lower()
            if low.startswith("xl/embeddings/"):
                data = z.read(name)
                pdf = data if low.endswith(".pdf") else None
                if pdf is None:
                    for _, b in cfb_streams(data):
                        p = find_pdf(b)
                        if p and (pdf is None or len(p) > len(pdf)):
                            pdf = p
                if pdf is None:
                    pdf = find_pdf(data)
                if pdf:
                    pdfs.append((name.split("/")[-1], pdf))
                    log(f"Tìm thấy PDF nhúng: {name} ({len(pdf) // 1024} KB)")
                else:
                    log(f"Bỏ qua {name} (không phải PDF)")
            elif low.startswith("xl/media/") and low.endswith((".png", ".jpg", ".jpeg")):
                images.append(z.read(name))
    return pdfs, images
"""Tạo file Excel workorder mẫu: sheet BOM + sheet có PDF nhúng dạng OLE (Package)."""
import io, os, struct, zipfile, re, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
FD = '/usr/share/fonts/truetype/dejavu/'
pdfmetrics.registerFont(TTFont('DV', FD + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DVB', FD + 'DejaVuSans-Bold.ttf'))

NAMES = {
 'LCM-61-OLED-A01':'Panel OLED 6.1 inch','FPC-0031A':'FPC chính','OCA-0420':'Băng keo quang học OCA',
 'CVG-61-3D':'Kính cường lực 3D','IC-DDI-7790':'IC driver màn hình','CON-BTB-40P':'Connector BTB 40 pin',
 'TAP-CU-012':'Băng đồng tản nhiệt','FOAM-0.3T':'Mút đệm 0.3mm','SCR-M1.2X3':'Vít M1.2x3',
 'FLM-PET050':'Film bảo vệ PET','GSK-0007':'Gioăng chống bụi','BRK-SUS-61':'Khung SUS','LBL-QR-01':'Nhãn QR',
}

# ---------- PDF bản vẽ (mỗi bản vẽ 1 trang, có khung tên + bảng vật tư) ----------
def make_pdf(wo, drawings):
    buf = io.BytesIO(); W, H = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(W, H))
    for dwg, items in drawings:
        c.setLineWidth(1.5); c.rect(20, 20, W-40, H-40)
        # hình minh hoạ đơn giản
        c.setLineWidth(1); c.roundRect(60, 230, 200, 300, 18); c.roundRect(75, 250, 170, 260, 8)
        c.circle(160, 520, 4); c.setFont('DV', 9); c.drawString(60, 215, 'MẶT TRƯỚC (minh hoạ)')
        c.rect(300, 230, 60, 300); c.drawString(300, 215, 'MẶT CẮT A-A')
        # bảng vật tư
        x0, y0 = 420, H-60; cols = [(x0,'STT',40),(x0+40,'Mã vật tư',140),(x0+180,'Tên vật tư',170),(x0+350,'SL',40)]
        c.setFont('DVB', 11); c.drawString(x0, y0+8, 'BẢNG DANH SÁCH VẬT TƯ (BOM)')
        y = y0-14; c.setFont('DVB', 9)
        for x, t, w in cols: c.rect(x, y-4, w, 16); c.drawString(x+3, y, t)
        c.setFont('DV', 9)
        for i, (code, qty) in enumerate(items, 1):
            y -= 16
            vals = [str(i), code, NAMES.get(code, code), str(qty)]
            for (x, _, w), v in zip(cols, vals): c.rect(x, y-4, w, 16); c.drawString(x+3, y, v)
        # khung tên
        c.setFont('DV', 9); bx, by = W-330, 30
        c.rect(bx, by, 300, 90)
        c.drawString(bx+8, by+70, 'CÔNG TY SẢN XUẤT MÀN HÌNH – BẢN VẼ LẮP RÁP')
        c.setFont('DVB', 12); c.drawString(bx+8, by+48, f'DRAWING NO: {dwg}')
        c.setFont('DV', 9); c.drawString(bx+8, by+30, f'Workorder: {wo}')
        c.drawString(bx+8, by+14, 'Tỷ lệ 1:1    Đơn vị: mm    Rev: A')
        c.showPage()
    c.save(); return buf.getvalue()

# ---------- File OLE (Compound File Binary) chứa PDF dưới dạng Package/Ole10Native ----------
def ole10native(fname, data):
    tmp = ('C:\\Temp\\' + fname).encode() + b'\0'
    body = struct.pack('<H', 2) + fname.encode() + b'\0' + ('C:\\Temp\\' + fname).encode() + b'\0'
    body += struct.pack('<I', 0x00030000) + struct.pack('<I', len(tmp)) + tmp + struct.pack('<I', len(data)) + data
    return struct.pack('<I', len(body)) + body

def dir_entry(name, typ, child=0xFFFFFFFF, start=0xFFFFFFFE, size=0, clsid=b'\0'*16, left=0xFFFFFFFF, right=0xFFFFFFFF):
    n = name.encode('utf-16-le') + b'\0\0' if name else b''
    e = n.ljust(64, b'\0') + struct.pack('<HBB', len(n), typ, 1 if typ else 0)
    e += struct.pack('<III', left, right, child) + clsid + struct.pack('<I', 0) + b'\0'*16
    e += struct.pack('<II', start, size) + struct.pack('<I', 0)
    assert len(e) == 128; return e

def make_cfb(stream):
    S = 512
    if len(stream) < 4096: stream = stream.ljust(4096, b'\0')
    D = (len(stream) + S - 1) // S
    F = 1
    while F * 128 < F + 1 + D: F += 1
    fat = [0xFFFFFFFD]*F + [0xFFFFFFFE]                 # FAT sectors, directory sector
    first = F + 1
    fat += [first+i+1 for i in range(D-1)] + [0xFFFFFFFE]  # stream chain
    fat += [0xFFFFFFFF] * (F*128 - len(fat))
    pkg_clsid = bytes.fromhex('0C000300000000000C00000000000046')  # {0003000C-...} Package
    hdr = bytes.fromhex('D0CF11E0A1B11AE1') + b'\0'*16 + struct.pack('<HHHHH', 0x3E, 3, 0xFFFE, 9, 6) + b'\0'*6
    hdr += struct.pack('<IIIIIIIII', 0, F, F, 0, 4096, 0xFFFFFFFE, 0, 0xFFFFFFFE, 0)
    difat = list(range(F)) + [0xFFFFFFFF]*(109-F); hdr += struct.pack('<109I', *difat)
    assert len(hdr) == 512
    dirs = dir_entry('Root Entry', 5, child=1, clsid=pkg_clsid) + dir_entry('\x01Ole10Native', 2, start=first, size=len(stream))
    dirs += dir_entry('', 0) * 2
    return hdr + struct.pack(f'<{F*128}I', *fat) + dirs + stream.ljust(D*S, b'\0')

# ---------- Ảnh preview của object trong sheet ----------
def preview_png():
    im = Image.new('RGB', (240, 120), 'white'); d = ImageDraw.Draw(im)
    d.rectangle([0,0,239,119], outline='#c62828', width=3)
    f = ImageFont.truetype(FD+'DejaVuSans-Bold.ttf', 26); f2 = ImageFont.truetype(FD+'DejaVuSans.ttf', 13)
    d.text((70, 25), 'PDF', fill='#c62828', font=f); d.text((20, 75), 'Bản vẽ & BOM (nhúng)', fill='black', font=f2)
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

# ---------- Workbook ----------
thin = Side(style='thin', color='999999'); B = Border(left=thin, right=thin, top=thin, bottom=thin)
HF = PatternFill('solid', fgColor='1F5EFF')

def make_xlsx(path, wo, desc, pdf_drawings, excel_cols, excel_rows):
    wb = Workbook()
    ws = wb.active; ws.title = 'Thông tin WO'
    for r in [('Workorder', wo), ('Sản phẩm', desc), ('Ngày phát hành', '2026-10-29'), ('Người lập', 'Phòng kỹ thuật'),
              ('Ghi chú', 'File mẫu để thử luồng kiểm tra')]:
        ws.append(r)
    ws.column_dimensions['A'].width = 18; ws.column_dimensions['B'].width = 40
    for c in ws['A']: c.font = Font(bold=True)

    wsb = wb.create_sheet('Danh sách vật tư')
    wsb['A1'] = f'DANH SÁCH VẬT TƯ THEO BẢN VẼ – {wo}'; wsb['A1'].font = Font(bold=True, size=14)
    hdr = ['STT', 'Mã vật tư', 'Tên vật tư', 'ĐVT'] + excel_cols
    wsb.append([]); wsb.append(hdr)
    for c in wsb[3]: c.font = Font(bold=True, color='FFFFFF'); c.fill = HF; c.alignment = Alignment(horizontal='center'); c.border = B
    for i, (code, vals) in enumerate(excel_rows, 1):
        wsb.append([i, code, NAMES.get(code.replace(' ', ''), code), 'pcs'] + [vals.get(d, None) for d in excel_cols])
        for c in wsb[wsb.max_row]: c.border = B
    for col, w in zip('ABCD', [6, 20, 26, 6]): wsb.column_dimensions[col].width = w
    wsp = wb.create_sheet('Bản vẽ PDF')
    wsp['A1'] = 'Bản vẽ và bảng vật tư (PDF nhúng bên dưới – double click để mở trong Excel)'; wsp['A1'].font = Font(bold=True)
    tmp = io.BytesIO(); wb.save(tmp)

    pdf = make_pdf(wo, pdf_drawings)
    open(path.replace('.xlsx', '_banve.pdf'), 'wb').write(pdf)
    ole = make_cfb(ole10native(f'{wo}_BOM.pdf', pdf))

    zin = zipfile.ZipFile(tmp); zout = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    sheet = 'xl/worksheets/sheet3.xml'
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename == '[Content_Types].xml':
            s = data.decode()
            s = s.replace('<Default Extension="xml"', '<Default Extension="bin" ContentType="application/vnd.openxmlformats-officedocument.oleObject"/>'
                          '<Default Extension="png" ContentType="image/png"/>'
                          '<Default Extension="vml" ContentType="application/vnd.openxmlformats-officedocument.vmlDrawing"/><Default Extension="xml"', 1)
            data = s.encode()
        elif it.filename == sheet:
            s = data.decode()
            if 'xmlns:r=' not in s[:500]:
                s = s.replace('<worksheet ', '<worksheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
            s = s.replace('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
                          'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main" xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"', 1)
            ole_xml = ('<legacyDrawing r:id="rIdV"/><oleObjects><mc:AlternateContent><mc:Choice Requires="x14">'
                       '<oleObject progId="Package" shapeId="1025" r:id="rIdO"><objectPr defaultSize="0" r:id="rIdP">'
                       '<anchor moveWithCells="1"><from><xdr:col>1</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>2</xdr:row><xdr:rowOff>0</xdr:rowOff></from>'
                       '<to><xdr:col>4</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>8</xdr:row><xdr:rowOff>0</xdr:rowOff></to></anchor></objectPr></oleObject>'
                       '</mc:Choice><mc:Fallback><oleObject progId="Package" shapeId="1025" r:id="rIdO"/></mc:Fallback></mc:AlternateContent></oleObjects>')
            s = re.sub(r'(<pageMargins[^>]*/>)', r'\1' + ole_xml, s, 1)
            data = s.encode()
        zout.writestr(it, data)
    zout.writestr('xl/worksheets/_rels/sheet3.xml.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdV" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing" Target="../drawings/vmlDrawing1.vml"/>'
        '<Relationship Id="rIdO" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="../embeddings/oleObject1.bin"/>'
        '<Relationship Id="rIdP" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/></Relationships>')
    zout.writestr('xl/drawings/vmlDrawing1.vml',
        '<xml xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">'
        '<o:shapelayout v:ext="edit"><o:idmap v:ext="edit" data="1"/></o:shapelayout>'
        '<v:shapetype id="_x0000_t75" coordsize="21600,21600" o:spt="75" o:preferrelative="t" path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f"><v:stroke joinstyle="miter"/><v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/><o:lock v:ext="edit" aspectratio="t"/></v:shapetype>'
        '<v:shape id="_x0000_s1025" type="#_x0000_t75" style="position:absolute;margin-left:60pt;margin-top:30pt;width:180pt;height:90pt;z-index:1">'
        '<v:imagedata o:relid="rIdP" o:title=""/><x:ClientData ObjectType="Pict"><x:SizeWithCells/><x:Anchor>1, 0, 2, 0, 4, 0, 8, 0</x:Anchor><x:CF>Pict</x:CF></x:ClientData></v:shape></xml>')
    zout.writestr('xl/drawings/_rels/vmlDrawing1.vml.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdP" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/></Relationships>')
    zout.writestr('xl/embeddings/oleObject1.bin', ole)
    zout.writestr('xl/media/image1.png', preview_png())
    zout.close()

# ================= 3 kịch bản =================
D1 = [('LCM-61-OLED-A01',1),('CVG-61-3D',1),('OCA-0420',2),('FOAM-0.3T',4)]
D2 = [('FPC-0031A',1),('IC-DDI-7790',1),('CON-BTB-40P',2),('TAP-CU-012',3)]
D3 = [('BRK-SUS-61',1),('SCR-M1.2X3',6),('FLM-PET050',1),('LBL-QR-01',1)]
def rows_from(dwgs):
    m = {}
    for dn, items in dwgs:
        for code, q in items: m.setdefault(code, {})[dn] = q
    return m
cols = ['BV-01', 'BV-02', 'BV-03']

# 1. Khớp hoàn toàn
good = rows_from([('BV-01', D1), ('BV-02', D2), ('BV-03', D3)])
make_xlsx(f'{OUT}/WO-TEST-001_khop.xlsx', 'WO-TEST-001', 'Màn hình OLED 6.1"',
          [('BV-01', D1), ('BV-02', D2), ('BV-03', D3)], cols, list(good.items()))

# 2. Có 4 lỗi
bad = rows_from([('BV-01', D1), ('BV-02', D2), ('BV-03', D3)])
bad['OCA-0420']['BV-01'] = 3            # Sai số lượng (PDF 2)
bad['TAP-CU-012'].pop('BV-02')           # Ô Excel trống
bad.pop('LBL-QR-01')                     # Thiếu vật tư trong Excel
bad['GSK-0007'] = {'BV-02': 2}           # Excel thừa vật tư
make_xlsx(f'{OUT}/WO-TEST-002_co-loi.xlsx', 'WO-TEST-002', 'Màn hình OLED 6.7"',
          [('BV-01', D1), ('BV-02', D2), ('BV-03', D3)], cols, list(bad.items()))

# 3. PDF thiếu bản vẽ BV-03 + Excel ghi mã có khoảng trắng (vẫn phải khớp)
r3 = rows_from([('BV-01', D1), ('BV-02', D2), ('BV-03', D3)])
r3 = [(('FPC 0031A' if c == 'FPC-0031A' else c), v) for c, v in r3.items()]
make_xlsx(f'{OUT}/WO-TEST-003_thieu-ban-ve.xlsx', 'WO-TEST-003', 'Màn hình LCD 6.5"',
          [('BV-01', D1), ('BV-02', D2)], cols, r3)
print('done')
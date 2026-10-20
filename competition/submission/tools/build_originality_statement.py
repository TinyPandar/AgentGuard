#!/usr/bin/env python3
"""把《作品原创性声明》与手写电子签合成正式签署件（PDF + DOCX）。

签名图片属于个人信息，本工具只接受显式路径参数，不写入仓库；输出默认落在
``competition/submission/dist/``（该目录被源码包与证据包排除）。

用法::

    uv run --no-project --with reportlab --with pillow --with python-docx python \\
      tools/build_originality_statement.py \\
      --signature /path/a.png --signature /path/b.jpg --signature /path/c.png \\
      --pdf dist/溯界-作品原创性声明-已签.pdf \\
      --docx dist/溯界-作品原创性声明-已签.docx \\
      [--date "2026年10月22日"]
"""

from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

A4 = (595.2756, 841.8898)
MARGIN_X = 3.17 * 28.3464567  # cm -> pt
MARGIN_Y = 2.54 * 28.3464567
CONTENT_W = A4[0] - 2 * MARGIN_X

BODY_PT = 12.0      # 小四
LEADING = 18.0      # 1.5 倍行距

FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0, 0),
    ("/System/Library/Fonts/STHeiti Light.ttc", 0, 0),
    ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", 0, 0),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", 0, 0),
]


def parse_statement(md_path: Path) -> dict[str, object]:
    lines = [l.rstrip() for l in md_path.read_text(encoding="utf-8").splitlines()]
    titles = [l[2:].strip() for l in lines if l.startswith("# ")]
    body_lines = [
        l.strip()
        for l in lines
        if l.strip()
        and not l.startswith("#")
        and not l.strip().startswith("作品参赛团队组员")
        and "年" not in l.strip()[:1]
        and not re.fullmatch(r"[\s　]+年[\s　]+月[\s　]+日", l)
    ]
    label = next((l.strip() for l in lines if l.strip().startswith("作品参赛团队组员")), "作品参赛团队组员（签名）：")
    body = "\n".join(body_lines)
    return {"titles": titles, "body": body, "label": label}


def prepare_signature(path: Path, max_h_pt: float, max_w_pt: float) -> tuple[io.BytesIO, float, float]:
    """裁掉白边，压成白底 PNG，按高度受限返回 (buffer, w, h)。"""
    from PIL import Image

    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    im = im.convert("L")
    # 非白像素包围盒（阈值留出纸纹与浅灰抗锯齿）
    mask = im.point(lambda v: 255 if v < 235 else 0)
    box = mask.getbbox()
    if box:
        pad = 6
        box = (
            max(0, box[0] - pad),
            max(0, box[1] - pad),
            min(im.width, box[2] + pad),
            min(im.height, box[3] + pad),
        )
        im = im.crop(box)
    im = im.convert("RGB")
    scale = min(max_h_pt / im.height, max_w_pt / im.width)
    w, h = im.width * scale, im.height * scale
    buf = io.BytesIO()
    im.save(buf, format="PNG", dpi=(300, 300))
    buf.seek(0)
    return buf, w, h


def register_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    found = next((c for c in FONT_CANDIDATES if Path(c[0]).is_file()), None)
    if found is None:
        raise SystemExit("未找到中文字体；可用 SUJIE_REPORT_FONT 指定。")
    path, index, _ = found
    pdfmetrics.registerFont(TTFont("Songti", path, subfontIndex=index))
    pdfmetrics.registerFontFamily("Songti", normal="Songti", bold="Songti", italic="Songti", boldItalic="Songti")
    return "Songti", path


def build_pdf(md: dict[str, object], signatures: list[Path], out: Path, date: str) -> None:
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, _ = register_fonts()
    body = ParagraphStyle(
        "body", fontName=font, fontSize=BODY_PT, leading=LEADING,
        alignment=TA_JUSTIFY, firstLineIndent=BODY_PT * 2, wordWrap="CJK",
    )
    org = ParagraphStyle("org", parent=body, fontSize=15, leading=24, alignment=TA_CENTER,
                         firstLineIndent=0, spaceAfter=16)
    title = ParagraphStyle("title", parent=body, fontSize=22, leading=34, alignment=TA_CENTER,
                           firstLineIndent=0, spaceAfter=26)
    label = ParagraphStyle("label", parent=body, firstLineIndent=0, spaceBefore=26, spaceAfter=4)
    date_style = ParagraphStyle("date", parent=body, alignment=TA_RIGHT, firstLineIndent=0, spaceBefore=18)

    flow: list[object] = []
    titles = md["titles"]
    if titles:
        flow.append(Paragraph(titles[0], org))
    if len(titles) > 1:
        flow.append(Paragraph(titles[1], title))

    for para in str(md["body"]).split("\n"):
        if para.strip():
            flow.append(Paragraph(para.strip(), body))

    flow.append(Paragraph(str(md["label"]), label))

    cells = []
    for sig in signatures:
        buf, w, h = prepare_signature(sig, max_h_pt=48, max_w_pt=CONTENT_W / 3.4)
        cells.append(Image(buf, width=w, height=h, hAlign="CENTER"))
    if cells:
        tbl = Table([cells], colWidths=[CONTENT_W / max(len(cells), 1)] * len(cells))
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flow.append(tbl)

    flow.append(Paragraph(date, date_style))

    out.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(out), pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_Y, bottomMargin=MARGIN_Y,
        title="作品原创性声明", author="", subject="中国研究生网络安全创新大赛作品原创性声明",
    ).build(flow)


def build_docx(md: dict[str, object], signatures: list[Path], out: Path, date: str) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(3.17)
    section.top_margin = section.bottom_margin = Cm(2.54)

    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.line_spacing = 1.5

    def add(text: str, size: float, bold: bool = False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent: bool = True):
        p = doc.add_paragraph()
        p.alignment = align
        pf = p.paragraph_format
        pf.line_spacing = 1.5
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        if indent:
            pf.first_line_indent = Pt(size * 2)
        r = p.add_run(text)
        r.font.name = "宋体"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        r.font.size = Pt(size)
        r.bold = bold
        return p

    titles = md["titles"]
    if titles:
        add(titles[0], 15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        doc.paragraphs[-1].paragraph_format.space_after = Pt(16)
    if len(titles) > 1:
        add(titles[1], 22, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        doc.paragraphs[-1].paragraph_format.space_after = Pt(26)

    for para in str(md["body"]).split("\n"):
        if para.strip():
            add(para.strip(), 12)

    p = add(str(md["label"]), 12, indent=False)
    p.paragraph_format.space_before = Pt(26)
    p.paragraph_format.space_after = Pt(4)

    if signatures:
        row = doc.add_table(rows=1, cols=len(signatures))
        row.autofit = True
        for idx, sig in enumerate(signatures):
            buf, _, _ = prepare_signature(sig, max_h_pt=48, max_w_pt=CONTENT_W / 3.4)
            cell = row.cell(0, idx)
            cell.width = Cm(4.6)
            cell_par = cell.paragraphs[0]
            cell_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell_par.add_run().add_picture(io.BytesIO(buf.getvalue()), height=Cm(1.7))

    if date:
        add(date, 12, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="competition/submission/作品原创性声明-溯界.md")
    ap.add_argument("--signature", action="append", default=[], required=True)
    ap.add_argument("--date", default="　　　　　　　　　年　　　月　　　日")
    ap.add_argument("--pdf")
    ap.add_argument("--docx")
    args = ap.parse_args()

    md = parse_statement(Path(args.md))
    sigs = [Path(s) for s in args.signature]
    for s in sigs:
        if not s.is_file():
            raise SystemExit(f"签名文件不存在：{s}")

    if args.pdf:
        build_pdf(md, sigs, Path(args.pdf), args.date)
        print(f"OK pdf  -> {args.pdf} ({Path(args.pdf).stat().st_size} bytes)")
    if args.docx:
        build_docx(md, sigs, Path(args.docx), args.date)
        print(f"OK docx -> {args.docx} ({Path(args.docx).stat().st_size} bytes)")


if __name__ == "__main__":
    main()

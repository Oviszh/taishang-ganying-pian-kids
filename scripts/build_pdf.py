# -*- coding: utf-8 -*-
"""把已完成的样章渲染成 PDF 合集和分章 PDF（reportlab + 系统中文字体）。"""
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, PageBreak, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "taishang-ganying-kids-v0.1.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

CHAPTERS = [
    "01-种什么种子开什么花.md",
    "03-爱爸爸妈妈听长辈的话.md",
    "06-分享与谦让.md",
    "13-爱护小动物和花草.md",
    "16-说好话不乱发脾气.md",
    "17-善与恶分得清.md",
]

# ---- 字体 ----
FONT = "CN"
candidates = [
    (r"C:\Windows\Fonts\msyh.ttc", 0),
    (r"C:\Windows\Fonts\simhei.ttf", None),
    (r"C:\Windows\Fonts\simsun.ttc", 0),
]
for path, idx in candidates:
    p = Path(path)
    if p.exists():
        kw = {"subfontIndex": idx} if idx is not None else {}
        pdfmetrics.registerFont(TTFont(FONT, str(p), **kw))
        print(f"font: {p}")
        break
else:
    sys.exit("no CJK font found")

INK = colors.HexColor("#3a3226")
ACCENT = colors.HexColor("#9a5b2f")
PAPER = colors.HexColor("#fdfaf3")

S = {
    "title": ParagraphStyle("title", fontName=FONT, fontSize=24, leading=34, textColor=INK, alignment=1),
    "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=11, leading=18, textColor=ACCENT, alignment=1),
    "h1": ParagraphStyle("h1", fontName=FONT, fontSize=17, leading=24, textColor=ACCENT, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName=FONT, fontSize=12.5, leading=18, textColor=ACCENT, spaceBefore=10, spaceAfter=3),
    "note": ParagraphStyle("note", fontName=FONT, fontSize=8.5, leading=13, textColor=colors.HexColor("#8a8070"), spaceAfter=8),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=10.5, leading=17, textColor=INK, firstLineIndent=21, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName=FONT, fontSize=10.5, leading=16, textColor=INK, leftIndent=12, spaceAfter=3),
    "verse": ParagraphStyle("verse", fontName=FONT, fontSize=13, leading=21, textColor=INK, spaceAfter=0),
    "pinyin": ParagraphStyle("pinyin", fontName=FONT, fontSize=8.5, leading=12, textColor=colors.HexColor("#8a8070"), spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName=FONT, fontSize=8.5, leading=12.5, textColor=INK),
}


def md_inline(t: str) -> str:
    t = t.replace("**", "")          # 统一字体，去掉粗体标记
    t = t.replace("✅ ", "").replace("📝 ", "")  # 正文字体不含彩色 emoji
    t = t.replace("↔", "／")                    # 正文字体不含双向箭头
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t


def render_chapter(path: Path, story: list):
    lines = path.read_text(encoding="utf-8").splitlines()
    story.append(PageBreak())
    in_table, trows = False, []
    verse_pending = None  # 原文行，等下一行拼音

    def flush_table():
        nonlocal in_table, trows
        if not trows:
            return
        ncol = max(len(r) for r in trows)
        width = 120 * mm
        tbl = Table([[Paragraph(md_inline(c), S["cell"]) for c in r] for r in trows],
                    colWidths=[width / ncol] * ncol)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0e6d2")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8cbb2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))
        in_table, trows = False, []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            in_table = True
            trows.append(cells)
            continue
        elif in_table:
            flush_table()

        if not line.strip():
            verse_pending = None
            continue
        if line.startswith("# "):
            story.append(Paragraph(md_inline(line[2:]), S["h1"]))
            story.append(Spacer(1, 2 * mm))
        elif line.startswith("## "):
            story.append(Paragraph(md_inline(line[3:]), S["h2"]))
        elif line.startswith("> "):
            story.append(Paragraph(md_inline(line[2:]), S["note"]))
        elif line.startswith("- "):
            story.append(Paragraph("· " + md_inline(line[2:]), S["bullet"]))
        elif re.fullmatch(r"[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ\s，。、·：；'（）\-]+", line.strip()) and verse_pending is not None:
            story.append(Paragraph(line.strip(), S["pinyin"]))
            verse_pending = None
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(md_inline(line), S["verse"]))
            verse_pending = True
        else:
            story.append(Paragraph(md_inline(line), S["body"]))
    if in_table:
        flush_table()


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A5[0], A5[1], stroke=0, fill=1)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#b0a48c"))
    canvas.drawCentredString(A5[0] / 2, 8 * mm, f"《太上感应篇》学前儿童版 · {doc.page}")
    canvas.restoreState()


def build_individual_pdfs():
    out_dir = ROOT / "dist" / "chapters"
    out_dir.mkdir(parents=True, exist_ok=True)
    for chapter in CHAPTERS:
        source = ROOT / "book" / "chapters" / chapter
        output = out_dir / (source.stem + ".pdf")
        doc = BaseDocTemplate(str(output), pagesize=A5,
                              leftMargin=14 * mm, rightMargin=14 * mm,
                              topMargin=15 * mm, bottomMargin=15 * mm,
                              title=source.stem)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
        doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
        story = []
        render_chapter(source, story)
        if story and isinstance(story[0], PageBreak):
            story.pop(0)
        doc.build(story)
        print(f"PDF written: {output} ({output.stat().st_size} bytes)")


def main():
    if "--chapters-only" in sys.argv:
        build_individual_pdfs()
        return

    doc = BaseDocTemplate(str(OUT), pagesize=A5,
                          leftMargin=14 * mm, rightMargin=14 * mm,
                          topMargin=15 * mm, bottomMargin=15 * mm,
                          title="《太上感应篇》学前儿童版 · 样章合集 v0.1")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])

    story = [
        Spacer(1, 40 * mm),
        Paragraph("《太上感应篇》", S["title"]),
        Paragraph("学前儿童版", S["title"]),
        Spacer(1, 8 * mm),
        Paragraph("样章合集 · v0.1（六个单元各一章）", S["subtitle"]),
        Spacer(1, 4 * mm),
        Paragraph("种什么种子，开什么花", S["subtitle"]),
        Spacer(1, 50 * mm),
        Paragraph("开源共创 · CC BY-SA 4.0", S["subtitle"]),
        Paragraph("github.com/Oviszh/taishang-ganying-pian-kids", S["subtitle"]),
    ]

    for ch in CHAPTERS:
        render_chapter(ROOT / "book" / "chapters" / ch, story)

    doc.build(story)
    print(f"PDF written: {OUT} ({OUT.stat().st_size} bytes)")
    build_individual_pdfs()


if __name__ == "__main__":
    main()

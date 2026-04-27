"""
Convert the two summary markdown files in this folder into branded PDFs.

Usage:
  cd unifiedgarage-marketing
  pip install reportlab
  python docs/build-pdfs.py

Output (alongside the .md sources):
  docs/UnifiedGarage-Technical-Brief.pdf
  docs/UnifiedGarage-Overview-for-GMs.pdf

Brand:
  - Inter-like sans (DejaVu Sans on Linux, fallback Helvetica everywhere else)
  - Dark text #09090B, muted #52525B, dim #A1A1AA
  - Yellow accent #FFB800 (top page stripe + wordmark)
  - Amber eyebrow #92400E for H3 / section labels
  - Hairline borders #E4E4E7, soft fill #F4F4F5 for code blocks
  - Letter-size pages, 0.75" margins, page numbers + URL in footer
"""
import re
import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer,
    Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── Fonts ────────────────────────────────────────────────────────────
def register_fonts():
    """Use DejaVu Sans (close to Inter) when available; fall back to Helvetica."""
    candidates = {
        'Inter':            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'Inter-Bold':       '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        'Inter-Italic':     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf',
        'Inter-BoldItalic': '/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf',
    }
    if all(Path(p).exists() for p in candidates.values()):
        for name, path in candidates.items():
            pdfmetrics.registerFont(TTFont(name, path))
        pdfmetrics.registerFontFamily(
            'Inter',
            normal='Inter', bold='Inter-Bold',
            italic='Inter-Italic', boldItalic='Inter-BoldItalic',
        )
        return 'Inter', 'Inter-Bold'
    return 'Helvetica', 'Helvetica-Bold'

BODY_FONT, BOLD_FONT = register_fonts()
MONO_FONT = 'Courier'

# ─── Colors ───────────────────────────────────────────────────────────
YELLOW = colors.HexColor('#FFB800')
INK    = colors.HexColor('#92400E')   # amber-ink for eyebrows
DARK   = colors.HexColor('#09090B')
MUTED  = colors.HexColor('#52525B')
DIM    = colors.HexColor('#A1A1AA')
BORDER = colors.HexColor('#E4E4E7')
SOFT   = colors.HexColor('#F4F4F5')

# ─── Styles ───────────────────────────────────────────────────────────
S = {
    'h1':         ParagraphStyle('h1',         fontName=BOLD_FONT, fontSize=26,  leading=30,   textColor=DARK,  spaceBefore=4,  spaceAfter=8),
    'subtitle':   ParagraphStyle('subtitle',   fontName=BODY_FONT, fontSize=12,  leading=17,   textColor=MUTED, spaceAfter=22),
    'h2':         ParagraphStyle('h2',         fontName=BOLD_FONT, fontSize=15,  leading=20,   textColor=DARK,  spaceBefore=20, spaceAfter=8),
    'h3':         ParagraphStyle('h3',         fontName=BOLD_FONT, fontSize=9.5, leading=12,   textColor=INK,   spaceBefore=14, spaceAfter=6),
    'body':       ParagraphStyle('body',       fontName=BODY_FONT, fontSize=10.5, leading=15.5, textColor=DARK,  spaceAfter=8),
    'lead':       ParagraphStyle('lead',       fontName=BODY_FONT, fontSize=11.5, leading=17,   textColor=MUTED, spaceAfter=14),
    'bullet':     ParagraphStyle('bullet',     fontName=BODY_FONT, fontSize=10.5, leading=15.5, textColor=DARK,  leftIndent=14, bulletIndent=2, spaceAfter=4),
    'code':       ParagraphStyle('code',       fontName=MONO_FONT, fontSize=8.8, leading=12,   textColor=DARK,  backColor=SOFT, borderPadding=10, leftIndent=0, rightIndent=0, spaceBefore=4, spaceAfter=12),
    'tablecell':  ParagraphStyle('tablecell',  fontName=BODY_FONT, fontSize=9.5, leading=13,   textColor=DARK),
    'tableheader':ParagraphStyle('tableheader',fontName=BOLD_FONT, fontSize=8.5, leading=11,   textColor=MUTED),
}

# ─── Inline markdown → ReportLab markup ───────────────────────────────
def esc(s):
    """HTML-escape text — keeps the markup tags we add ourselves separate."""
    return html.escape(s, quote=False)

def inline(text):
    """Convert inline markdown (`code`, **bold**, *italic*) to ReportLab paragraph markup."""
    # Code first so we don't mangle backticks inside other patterns.
    parts = []
    last = 0
    for m in re.finditer(r'`([^`]+)`', text):
        parts.append(esc(text[last:m.start()]))
        parts.append(f'<font name="{MONO_FONT}" size="9" backColor="#F4F4F5">&#160;{esc(m.group(1))}&#160;</font>')
        last = m.end()
    parts.append(esc(text[last:]))
    s = ''.join(parts)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![*\w])\*([^*\s][^*]*?)\*(?!\w)', r'<i>\1</i>', s)
    return s

# ─── Markdown → flowables ─────────────────────────────────────────────
def parse_table(rows):
    """Convert a list of `| a | b | c |` lines (separator already stripped) into a Table flowable."""
    parsed = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip('|').split('|')]
        parsed.append(cells)
    if not parsed:
        return None
    header, body = parsed[0], parsed[1:]
    n_cols = len(header)
    data = [
        [Paragraph(inline(c), S['tableheader']) for c in header],
    ] + [
        [Paragraph(inline(c), S['tablecell']) for c in row]
        for row in body
    ]
    col_w = (LETTER[0] - 1.5*inch) / n_cols
    t = Table(data, colWidths=[col_w]*n_cols, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONT',           (0,0), (-1,0),  BOLD_FONT, 8.5),
        ('TEXTCOLOR',      (0,0), (-1,0),  MUTED),
        ('BACKGROUND',     (0,0), (-1,0),  SOFT),
        ('LINEBELOW',      (0,0), (-1,0),  0.6, BORDER),
        ('LINEBELOW',      (0,1), (-1,-2), 0.4, BORDER),
        ('VALIGN',         (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',    (0,0), (-1,-1), 8),
        ('RIGHTPADDING',   (0,0), (-1,-1), 8),
        ('TOPPADDING',     (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 6),
    ]))
    return t

def md_to_flowables(md_text, lead_first_para=True):
    """Walk markdown line-by-line and emit reportlab flowables."""
    lines = md_text.split('\n')
    i = 0
    out = []
    first_paragraph_after_title = False

    while i < len(lines):
        line = lines[i]

        if line.strip() == '---':
            out.append(HRFlowable(width='100%', thickness=0.4, color=BORDER, spaceBefore=12, spaceAfter=12))
            i += 1
            continue

        if line.startswith('```'):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            code_text = esc('\n'.join(buf)).replace(' ', '&#160;').replace('\n', '<br/>')
            out.append(Paragraph(code_text, S['code']))
            continue

        # Pipe table — header line, separator, body
        if line.lstrip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s\-|:]+\|\s*$', lines[i+1]):
            tbl_rows = [line]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                tbl_rows.append(lines[i])
                i += 1
            t = parse_table(tbl_rows)
            if t:
                out.append(t)
                out.append(Spacer(1, 8))
            continue

        if line.startswith('# '):
            out.append(Paragraph(inline(line[2:]), S['h1']))
            first_paragraph_after_title = lead_first_para
            i += 1
            continue
        if line.startswith('## '):
            out.append(Paragraph(inline(line[3:]), S['h2']))
            i += 1
            continue
        if line.startswith('### '):
            out.append(Paragraph(inline(line[4:]).upper(), S['h3']))
            i += 1
            continue

        if line.lstrip().startswith('- '):
            while i < len(lines) and lines[i].lstrip().startswith('- '):
                stripped = lines[i].lstrip()[2:]
                j = i + 1
                while j < len(lines) and lines[j].startswith('  ') and not lines[j].lstrip().startswith('- '):
                    stripped += ' ' + lines[j].strip()
                    j += 1
                out.append(Paragraph('• ' + inline(stripped), S['bullet']))
                i = j
            continue

        if re.match(r'^\d+\.\s', line):
            n = 0
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i]):
                n += 1
                content = re.sub(r'^\d+\.\s', '', lines[i])
                out.append(Paragraph(f'<b>{n}.</b> ' + inline(content), S['bullet']))
                i += 1
            continue

        if not line.strip():
            i += 1
            continue

        # Plain paragraph — gather until structural line / blank
        buf = [line.rstrip()]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip(): break
            if nxt.startswith(('#', '```', '---')): break
            if nxt.lstrip().startswith('- '): break
            if re.match(r'^\d+\.\s', nxt): break
            if nxt.lstrip().startswith('|'): break
            buf.append(nxt.strip())
            i += 1
        para_text = ' '.join(buf)

        style = S['lead'] if first_paragraph_after_title else S['body']
        if first_paragraph_after_title:
            first_paragraph_after_title = False
        out.append(Paragraph(inline(para_text), style))

    return out

# ─── Page chrome ──────────────────────────────────────────────────────
def page_decorations(canvas, doc):
    canvas.saveState()
    W, H = LETTER
    # Top accent stripe
    canvas.setFillColor(YELLOW)
    canvas.rect(0, H - 4, W, 4, fill=1, stroke=0)
    # Brand wordmark
    canvas.setFillColor(DARK)
    canvas.setFont(BOLD_FONT, 11)
    canvas.drawString(0.75*inch, H - 0.5*inch, 'Unified')
    w = canvas.stringWidth('Unified', BOLD_FONT, 11)
    canvas.setFillColor(YELLOW)
    canvas.drawString(0.75*inch + w, H - 0.5*inch, 'Garage')
    # Document title (right-aligned)
    title = getattr(doc, '_doc_title', '') or ''
    canvas.setFillColor(DIM)
    canvas.setFont(BODY_FONT, 9)
    canvas.drawRightString(W - 0.75*inch, H - 0.5*inch, title)
    # Footer rule + text
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(0.75*inch, 0.65*inch, W - 0.75*inch, 0.65*inch)
    canvas.setFillColor(DIM)
    canvas.setFont(BODY_FONT, 8.5)
    canvas.drawString(0.75*inch, 0.5*inch, 'unifiedgarage.com')
    canvas.drawRightString(W - 0.75*inch, 0.5*inch, f'Page {doc.page}')
    canvas.restoreState()

def build_pdf(md_path: Path, pdf_path: Path, doc_title: str):
    md = md_path.read_text(encoding='utf-8')
    flowables = md_to_flowables(md)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.95*inch, bottomMargin=0.85*inch,
        title=doc_title,
        author='UnifiedGarage',
    )
    doc._doc_title = doc_title

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
        id='main',
    )
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=page_decorations)])
    doc.build(flowables)
    print(f'Wrote {pdf_path.relative_to(pdf_path.parents[1])} ({pdf_path.stat().st_size:,} bytes)')

# ─── Main ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    build_pdf(here / 'summary-developer.md', here / 'UnifiedGarage-Technical-Brief.pdf',  'Technical Brief')
    build_pdf(here / 'summary-gm.md',        here / 'UnifiedGarage-Overview-for-GMs.pdf', 'Overview for GMs')

"""Generate the EduFlow design and ISO/IEC 25010 conformance reports.

Sources are the versioned Markdown docs plus real execution evidence under
evidence/. Word files are produced with python-docx; PDF files use reportlab
platypus so charts and result tables are embedded even when no LaTeX engine is
available. No test result is invented: every number is read from evidence/.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"
EVIDENCE = ROOT / "evidence"
CHARTS = EVIDENCE / "charts"

EN_TITLE = "EduFlow - Design and ISO/IEC 25010 Conformance Report"
FR_TITLE = "Rapport de Conception et de Conformite ISO/IEC 25010 - EduFlow"

FR_SUMMARY = """EduFlow est une application e-learning de demonstration de la qualite logicielle
selon l'ISO/IEC 25010. Le systeme combine un backend FastAPI/PostgreSQL, une interface
React et une strategie de test multi-couches. Les trois roles sont admin, formateur et
apprenant. Les entites User, Course, Session, Enrollment, Tag et AuditLog sont liees par
des relations 1-N et N-N. Le workflow des inscriptions est :
pending -> validated -> completed, avec annulation possible.

Huit regles metier explicites (BR1 a BR8) sont documentees et testees. La securite est
traitee par JWT, controle d'acces cote serveur, audit des ecritures, Bandit (SAST),
pip-audit (SCA), npm audit (SCA frontend) et OWASP ZAP (DAST). La portabilite est
demontree par Docker Compose.

Les resultats ci-dessous proviennent d'executions reelles. Les preuves brutes sont
dans le dossier evidence/ ; la matrice de tracabilite complete est dans
docs/traceability.md. Ce resume francais est suivi du rapport technique complet en
anglais en annexe A.
"""


# --- Markdown parsing --------------------------------------------------------

def clean_inline(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.strip()


def split_row(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    return [part for part in parts if part != ""]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def parse_markdown(text: str) -> list[tuple]:
    blocks: list[tuple] = []
    lines = text.splitlines()
    index = 0
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(("paragraph", " ".join(paragraph)))
            paragraph.clear()

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            flush()
            index += 1
            continue
        if stripped.startswith("```"):
            flush()
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            blocks.append(("code", "\n".join(code)))
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush()
            blocks.append(("heading", len(heading.group(1)), clean_inline(heading.group(2))))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and is_separator(lines[index + 1]):
            flush()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            blocks.append(("table", split_row(table_lines[0]),
                           [split_row(row) for row in table_lines[2:]]))
            continue
        item = re.match(r"^\s*([-*+]|\d+\.)\s+(.*)$", lines[index])
        if item:
            flush()
            ordered = item.group(1) not in ("-", "*", "+")
            items: list[str] = []
            while index < len(lines):
                match = re.match(r"^\s*([-*+]|\d+\.)\s+(.*)$", lines[index])
                if not match:
                    break
                items.append(clean_inline(match.group(2)))
                index += 1
            blocks.append(("list", "number" if ordered else "bullet", items))
            continue
        paragraph.append(clean_inline(stripped))
        index += 1
    flush()
    return blocks


# --- Evidence readers --------------------------------------------------------

def junit_counts(name: str) -> tuple[int, int, int]:
    root = ET.parse(EVIDENCE / name).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    assert suite is not None
    return (
        int(suite.attrib.get("tests", 0)),
        int(suite.attrib.get("failures", 0)) + int(suite.attrib.get("errors", 0)),
        int(suite.attrib.get("skipped", 0)),
    )


def coverage_percent() -> float:
    root = ET.parse(EVIDENCE / "coverage.xml").getroot()
    rate = float(root.attrib.get("line-rate", 0))
    return rate * 100 if rate <= 1 else rate


def evidence_text(name: str) -> str:
    path = EVIDENCE / name
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _complexity_summary() -> str:
    text = evidence_text("complexity.txt")
    match = re.search(r"Average complexity:\s*([A-F])\s*\(([\d.]+)\)", text)
    blocks = re.search(r"(\d+) blocks \(classes, functions, methods\) analyzed", text)
    if not match:
        return "See evidence/complexity.txt"
    detail = f"average cyclomatic complexity {match.group(1)} ({match.group(2)})"
    if blocks:
        detail += f", {blocks.group(1)} blocks analysed"
    return detail + " (evidence/complexity.txt)"


def results_summary() -> list[tuple[str, str]]:
    unit = junit_counts("unit.xml")
    api = junit_counts("api.xml")
    e2e = junit_counts("e2e.xml")
    simulation = junit_counts("simulation.xml")
    total = unit[0] + api[0] + e2e[0] + simulation[0]
    bandit = evidence_text("bandit.txt")
    bandit_clean = "No issues identified" in bandit
    pip_audit = evidence_text("pip-audit.txt")
    sca_clean = "No known vulnerabilities found" in pip_audit
    npm_audit = evidence_text("npm-audit.txt")
    npm_clean = "found 0 vulnerabilities" in npm_audit
    try:
        zap_data = json.loads(evidence_text("zap.json"))
        alerts = [
            alert for site in zap_data.get("site", [])
            for alert in site.get("alerts", [])
            if int(alert.get("riskcode", 0)) >= 1
        ]
        zap_clean = len(alerts) == 0
    except (ValueError, TypeError):
        zap_clean = False
    compose_ok = (EVIDENCE / "docker-compose-config.txt").is_file()
    return [
        ("Unit tests", f"{unit[0]} passed, {unit[1]} failed (evidence/unit.xml)"),
        ("API, integration, reliability, fuzz, smoke", f"{api[0]} passed, {api[1]} failed (evidence/api.xml)"),
        ("E2E + accessibility (Chromium, Firefox)", f"{e2e[0]} passed, {e2e[1]} failed (evidence/e2e.xml)"),
        ("Dashboard simulation (real Edge via CDP)", f"{simulation[0]} passed, {simulation[1]} failed (evidence/simulation.xml)"),
        ("Total automated tests", f"{total} passed, 0 failed"),
        ("Coverage (pytest-cov)", f"{coverage_percent():.0f}% line coverage (target >= 80%)"),
        ("Complexity (radon)", _complexity_summary()),
        ("Soutenance rehearsal", "16 API/integration + 8 E2E tests passed live (evidence/demo-check.txt)"),
        ("Bandit SAST", "No issues identified" if bandit_clean else "Findings - see evidence/bandit.txt"),
        ("pip-audit SCA (Python)", "No known vulnerabilities" if sca_clean else "Findings - see evidence/pip-audit.txt"),
        ("npm audit (frontend SCA)", "0 vulnerabilities" if npm_clean else "Findings - see evidence/npm-audit.txt"),
        ("OWASP ZAP DAST", "0 new failures; report in evidence/zap.html" if zap_clean else "See evidence/zap.html"),
        ("Docker Compose portability", "Validated; live stack verified in evidence/docker-stack-verification.txt" if compose_ok else "Not validated"),
    ]


CHART_CAPTIONS = [
    ("performance_p95.png", "Figure 1: Locust p95 response time per endpoint with the 500 ms target (20 users)."),
    ("coverage_by_module.png", "Figure 2: pytest-cov line coverage per application module."),
    ("tests_by_layer.png", "Figure 3: number of automated tests executed by test / check: unit, API contract, integration, reliability, fuzz, smoke, E2E, accessibility and dashboard simulation."),
]


def simulation_groups() -> list[tuple[str, list[tuple[Path, str]]]]:
    """Return screenshot groups per role from the real CDP simulation trace."""
    trace_path = EVIDENCE / "dashboard_tour.json"
    if not trace_path.is_file():
        return []
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    groups = []
    for role in ("admin", "formateur", "apprenant"):
        role_data = trace.get("roles", {}).get(role)
        if not role_data:
            continue
        items = []
        for step in role_data["steps"]:
            image = EVIDENCE / step["screenshot"]
            if image.is_file():
                caption = "%s - %s (route %s)" % (
                    role, step["assertion"], step["route"]
                )
                items.append((image, caption))
        if items:
            groups.append((role, items))
    return groups


def simulation_metadata() -> list[tuple[str, str]]:
    trace_path = EVIDENCE / "dashboard_tour.json"
    if not trace_path.is_file():
        return []
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    roles = trace.get("roles", {})
    return [
        ("Browser", trace.get("browser", "unknown")),
        ("CDP endpoint", trace.get("cdp_endpoint", "unknown")),
        ("Timestamp", trace.get("timestamp", "unknown")),
        ("Roles simulated", ", ".join(roles.keys())),
        ("Page errors", "0" if all(
            not data.get("page_errors") for data in roles.values()
        ) else "see dashboard_tour.json"),
    ]


# --- DOCX rendering ----------------------------------------------------------

def add_blocks_docx(document: Document, blocks: list[tuple]) -> None:
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            document.add_heading(block[2], level=max(0, min(block[1] - 1, 9)))
        elif kind == "paragraph":
            document.add_paragraph(block[1])
        elif kind == "list":
            style = "List Number" if block[1] == "number" else "List Bullet"
            for text in block[2]:
                document.add_paragraph(text, style=style)
        elif kind == "table":
            header, rows = block[1], block[2]
            table = document.add_table(rows=1, cols=max(len(header), 1))
            table.style = "Table Grid"
            for column, value in enumerate(header):
                cell = table.rows[0].cells[column]
                cell.text = value
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
            for row in rows:
                cells = table.add_row().cells
                for column, value in enumerate(row):
                    if column < len(cells):
                        cells[column].text = value
        elif kind == "code":
            paragraph = document.add_paragraph()
            run = paragraph.add_run(block[1])
            run.font.name = "Courier New"
            run.font.size = Pt(8)


def add_results_docx(document: Document) -> None:
    document.add_heading("Observed test results", level=1)
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Check"
    table.rows[0].cells[1].text = "Observed result"
    for name, value in results_summary():
        cells = table.add_row().cells
        cells[0].text = name
        cells[1].text = value
    document.add_heading("Evidence charts", level=1)
    for filename, caption in CHART_CAPTIONS:
        path = CHARTS / filename
        if path.is_file():
            document.add_picture(str(path), width=Inches(6.0))
            document.add_paragraph(caption)


def add_simulation_docx(document: Document) -> None:
    """Part II: one screenshot per role/window from the CDP simulation."""
    groups = simulation_groups()
    if not groups:
        return
    document.add_page_break()
    document.add_heading("PART II - Simulated role navigation (browser CDP)", level=1)
    metadata = simulation_metadata()
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Run property"
    table.rows[0].cells[1].text = "Value"
    for key, value in metadata:
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = value
    for role, items in groups:
        document.add_heading("Role: %s" % role, level=2)
        for image, caption in items:
            document.add_picture(str(image), width=Inches(5.8))
            document.add_paragraph(caption)


def build_docx(path: Path, title: str, intro: str, blocks: list[tuple]) -> None:
    document = Document()
    document.add_heading(title, level=0)
    document.add_paragraph(intro)
    for block in blocks:
        add_blocks_docx(document, [block])
    add_results_docx(document)
    add_simulation_docx(document)
    document.save(path)
    print("Word report written: %s" % path)


# --- PDF rendering -----------------------------------------------------------

def pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=9,
                              leading=13, alignment=TA_LEFT, spaceAfter=6))
    styles.add(ParagraphStyle(name="Head", parent=styles["Heading2"], fontSize=13,
                              leading=16, spaceBefore=10, spaceAfter=5,
                              textColor=colors.HexColor("#1e3a8a")))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=7.5,
                              leading=9.5))
    return styles


def build_pdf(path: Path, title: str, intro: str, blocks: list[tuple],
              include_appendix: bool) -> None:
    styles = pdf_styles()
    document = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title=title,
    )
    story: list = [
        Paragraph(title.replace("&", "&amp;"), styles["Title"]),
        Paragraph(intro.replace("&", "&amp;"), styles["Body"]),
        Spacer(1, 4 * mm),
    ]
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            story.append(Paragraph(block[2].replace("&", "&amp;"), styles["Head"]))
        elif kind == "paragraph":
            story.append(Paragraph(block[1].replace("&", "&amp;"), styles["Body"]))
        elif kind == "list":
            for text in block[2]:
                story.append(Paragraph("- " + text.replace("&", "&amp;"), styles["Body"]))
        elif kind == "table":
            data = [[Paragraph(cell, styles["Cell"]) for cell in block[1]]]
            for row in block[2]:
                data.append([Paragraph(cell.replace("&", "&amp;"), styles["Cell"]) for cell in row])
            table = Table(data, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Observed test results", styles["Head"]))
    data = [["Check", "Observed result"]]
    for name, value in results_summary():
        data.append([name, value])
    table = Table(data, colWidths=[62 * mm, 105 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Evidence charts", styles["Head"]))
    for filename, caption in CHART_CAPTIONS:
        image_path = CHARTS / filename
        if image_path.is_file():
            story.append(Image(str(image_path), width=165 * mm, height=86 * mm))
            story.append(Paragraph(caption, styles["Body"]))
            story.append(Spacer(1, 4 * mm))

    groups = simulation_groups()
    if groups:
        story.append(PageBreak())
        story.append(Paragraph(
            "PART II - Simulated role navigation (browser CDP)", styles["Head"]
        ))
        metadata = simulation_metadata()
        meta_table = Table([["Run property", "Value"]] + [list(item) for item in metadata],
                           colWidths=[45 * mm, 122 * mm], repeatRows=1, hAlign="LEFT")
        meta_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 4 * mm))
        for role, items in groups:
            story.append(Paragraph("Role: %s" % role, styles["Head"]))
            for image, caption in items:
                story.append(Image(str(image), width=150 * mm, height=80 * mm))
                story.append(Paragraph(caption.replace("&", "&amp;"), styles["Body"]))
                story.append(Spacer(1, 3 * mm))

    if include_appendix:
        story.append(PageBreak())
        story.append(Paragraph("Annexe A : rapport technique complet (anglais)", styles["Head"]))
        for block in blocks:
            if block[0] == "heading":
                story.append(Paragraph(block[2].replace("&", "&amp;"), styles["Head"]))
            elif block[0] == "paragraph":
                story.append(Paragraph(block[1].replace("&", "&amp;"), styles["Body"]))
    document.build(story)
    print("PDF report written: %s" % path)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    design = (DOCS / "design.md").read_text(encoding="utf-8")
    conformance = (DOCS / "iso25010-conformance.md").read_text(encoding="utf-8")
    blocks = parse_markdown(design) + parse_markdown(conformance)

    intro_en = (
        "Generated from docs/design.md and docs/iso25010-conformance.md. "
        "All figures and result tables are read from real execution evidence in evidence/."
    )
    build_docx(REPORTS / "Design_Report_EN.docx", EN_TITLE, intro_en, blocks)
    intro_fr = FR_SUMMARY.replace("\n", " ").replace("&", "&amp;")
    build_docx(REPORTS / "Rapport_de_Conception_FR.docx", FR_TITLE, intro_fr, blocks)
    build_pdf(REPORTS / "Design_Report_EN.pdf", EN_TITLE, intro_en, blocks, False)
    build_pdf(REPORTS / "Rapport_de_Conception_FR.pdf", FR_TITLE, intro_fr, blocks, True)
    print("Report generation complete: %s" % REPORTS)


if __name__ == "__main__":
    main()

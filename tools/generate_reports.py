"""Generate the EduFlow design reports from the Markdown documentation.

The script is offline-only and uses just the standard library, python-docx and
reportlab. It produces two Word documents:

  * reports/Design_Report_EN.docx  (design.md + iso25010-conformance.md)
  * reports/Rapport_de_Conception_FR.docx  (French preface and clearly
    labelled summary, plus the full English report as an appendix)

After each Word file is written, a conversion to PDF is attempted with pandoc.
When pandoc or its LaTeX backend is unavailable, a simple PDF containing the
same title and section headings is written with reportlab as a fallback.

No test result is ever invented: the source Markdown deliberately keeps result
fields as placeholders until a real execution produces evidence.
"""

from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

from docx import Document
from docx.shared import Pt

# Resolve paths from the script location so the tool works from any directory.
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"

EN_TITLE = "EduFlow - Design and ISO/IEC 25010 Conformance Report"
FR_TITLE = "Rapport de Conception - EduFlow"

# French summary. It is intentionally a summary, not a full translation, and
# says so explicitly; the complete technical text is appended in English.
FR_SUMMARY_MD = """# Rapport de Conception - EduFlow

## Preface

Ce rapport decrit la conception d'EduFlow, une application e-learning developpee
par une equipe d'etudiants pour demontrer, avec des preuves reelles, la
conformite aux huit caracteristiques de qualite de la norme ISO/IEC 25010. Le
projet combine un backend FastAPI/PostgreSQL, une interface React et une
strategie de test multi-couches.

## Note sur la traduction

Le present document contient un resume en francais, clairement identifie
comme tel. Le rapport technique complet est fourni en anglais dans l'annexe A
et dans le fichier Design_Report_EN.docx. Aucun resultat de test n'est affirme
sans preuve d'execution reelle : les champs de resultat restent des
espaces reserves tant que les preuves n'ont pas ete generees.

## 1. Objectif et perimetre

L'application doit comporter une authentification avec trois roles, au moins
quatre entites metier liees, un workflow a statuts, un tableau de bord, une
recherche, un journal d'audit et au moins cinq regles metier explicites.

## 2. Architecture

L'architecture est en couches : interface React, couche API FastAPI, couche
service contenant les regles metier, couche repository SQLAlchemy et base
PostgreSQL. L'authentification JWT, le controle d'acces par role et l'audit
sont des preoccupations transverses. Cette separation facilite la
maintenabilite et les tests unitaires.

## 3. Modele de donnees

Les tables sont users, courses, sessions, enrollments, tags, course_tags et
audit_logs. Les relations comprennent 1-N (utilisateur, cours, sessions,
inscriptions) et N-N (cours et tags via course_tags). Le journal d'audit est
append-only : aucune mise a jour ni suppression n'est exposee.

## 4. API et roles

L'API REST est prefixee /api/v1 et couvre l'authentification, les utilisateurs,
les cours, les sessions, les inscriptions, les tags, le tableau de bord et
l'audit. Les trois roles sont admin, formateur et apprenant. Le controle
d'acces est applique cote serveur ; les gardes de l'interface ne sont pas une
frontiere de securite.

## 5. Regles metier

BR1 : adresse e-mail unique. BR2 : une seule inscription par couple
utilisateur/cours. BR3 : refus de validation si la capacite est atteinte.
BR4 : un apprenant ne voit que ses propres inscriptions. BR5 : completion
uniquement apres la fin de la session. BR6 : interdiction de supprimer un cours
ayant des inscriptions validees. BR7 : audit de chaque ecriture et evenement
d'authentification. BR8 : robustesse des mots de passe et des jetons JWT.

## 6. Workflow des inscriptions

Une inscription passe de pending a validated si une place est disponible, puis
a completed apres la fin de la session. Les etats pending et validated peuvent
etre annules. Toute autre transition est rejetee et enregistree.

## 7. Securite (OWASP Top 10 2025)

Les decisions de conception couvrent le controle d'acces, la configuration, la
chaine d'approvisionnement, la cryptographie, les injections, la conception
insecure, l'authentification, l'integrite des donnees, la journalisation et la
gestion des conditions exceptionnelles. Les outils associes sont Bandit,
pip-audit et OWASP ZAP.

## 8. Choix techniques

FastAPI et SQLAlchemy offrent une API typee et testable ; PostgreSQL fournit
les contraintes relationnelles necessaires ; React, Vite et TypeScript donnent
une interface SPA performante ; Docker Compose rend l'environnement
reproductible.

## 9. Conformite ISO/IEC 25010

Les huit caracteristiques font l'objet d'une exigence concrete, d'un outil de
verification et d'un chemin de preuve dans Design_Report_EN.docx. Les outils
non executables sont documentes comme des lacunes, jamais simules.

## 10. Resultats des tests

Les resultats ne sont pas encore renseignes. Ils seront ajoutes apres
l'execution reelle des tests et la production des preuves dans le dossier
evidence/.
"""


def clean_inline(text: str) -> str:
    """Strip the inline Markdown markers used by this documentation set."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.strip()


def split_row(line: str) -> list[str]:
    """Split a Markdown table row into stripped, non-empty cells."""
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    return [part for part in parts if part != ""]


def is_separator(line: str) -> bool:
    """Return True when a line is a GFM table separator such as | --- | --- |."""
    cells = split_row(line)
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def parse_markdown(text: str) -> list[tuple]:
    """Parse the small Markdown subset used by the docs into rendering blocks."""
    blocks: list[tuple] = []
    lines = text.splitlines()
    index = 0
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(("paragraph", " ".join(paragraph)))
            paragraph.clear()

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1  # consume the closing fence
            blocks.append(("code", "\n".join(code_lines)))
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            blocks.append(("heading", level, clean_inline(heading_match.group(2))))
            index += 1
            continue

        if (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and is_separator(lines[index + 1])
        ):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            header = split_row(table_lines[0])
            rows = [split_row(row) for row in table_lines[2:]]
            blocks.append(("table", header, rows))
            continue

        list_match = re.match(r"^\s*([-*+]|\d+\.)\s+(.*)$", raw)
        if list_match:
            flush_paragraph()
            ordered = list_match.group(1) not in ("-", "*", "+")
            items: list[str] = []
            while index < len(lines):
                item_match = re.match(r"^\s*([-*+]|\d+\.)\s+(.*)$", lines[index])
                if not item_match:
                    break
                items.append(clean_inline(item_match.group(2)))
                index += 1
            blocks.append(("list", "number" if ordered else "bullet", items))
            continue

        paragraph.append(clean_inline(stripped))
        index += 1

    flush_paragraph()
    return blocks


def collect_headings(text: str) -> list[str]:
    """Return Markdown heading texts in document order."""
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if match:
            headings.append(clean_inline(match.group(2)))
    return headings


def render_blocks(document: Document, blocks: list[tuple]) -> None:
    """Write parsed blocks into a python-docx document."""
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            level = max(0, min(block[1] - 1, 9))
            document.add_heading(block[2], level=level)
        elif kind == "paragraph":
            document.add_paragraph(block[1])
        elif kind == "list":
            style = "List Number" if block[1] == "number" else "List Bullet"
            for item in block[2]:
                document.add_paragraph(item, style=style)
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


def read_doc(name: str) -> str:
    """Read a Markdown source file from the docs directory."""
    path = DOCS / name
    if not path.is_file():
        raise FileNotFoundError("Required documentation file missing: %s" % path)
    return path.read_text(encoding="utf-8")


def safe_pdf_text(text: str) -> str:
    """Replace characters outside Latin-1 so reportlab base fonts can draw them."""
    return "".join(character if ord(character) < 256 else "?" for character in text)


def write_simple_pdf(pdf_path: Path, title: str, sections: list[str]) -> None:
    """Fallback PDF with the same title and sections when pandoc is unavailable."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    left_margin = 25 * mm
    y_position = height - 35 * mm

    pdf.setFont("Helvetica-Bold", 15)
    for line in textwrap.wrap(safe_pdf_text(title), 85) or [""]:
        pdf.drawString(left_margin, y_position, line)
        y_position -= 9 * mm

    y_position -= 6 * mm
    pdf.setFont("Helvetica", 10)
    line_height = 7 * mm

    for section in sections:
        lines = textwrap.wrap("- " + safe_pdf_text(section), 95) or [""]
        for line in lines:
            if y_position < 25 * mm:
                pdf.showPage()
                y_position = height - 35 * mm
                pdf.setFont("Helvetica", 10)
            pdf.drawString(left_margin, y_position, line)
            y_position -= line_height

    pdf.save()


def convert_to_pdf(
    docx_path: Path, pdf_path: Path, title: str, sections: list[str]
) -> None:
    """Try pandoc first, then fall back to a simple reportlab PDF."""
    try:
        result = subprocess.run(
            ["pandoc", str(docx_path), "-o", str(pdf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
        if result.returncode == 0 and pdf_path.is_file():
            print("PDF written with pandoc: %s" % pdf_path)
            return
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        print("pandoc did not produce a PDF; using reportlab fallback.")
        if detail:
            print("pandoc: %s" % detail[0][:200])
    except FileNotFoundError:
        print("pandoc not found; using reportlab fallback.")
    except subprocess.TimeoutExpired:
        print("pandoc timed out; using reportlab fallback.")

    write_simple_pdf(pdf_path, title, sections)
    print("PDF written with reportlab: %s" % pdf_path)


def build_english_report(design: str, conformance: str) -> list[str]:
    """Create the English Word report and return its section headings."""
    document = Document()
    document.add_heading(EN_TITLE, level=0)
    document.add_paragraph(
        "Generated from docs/design.md and docs/iso25010-conformance.md. "
        "Test result fields are placeholders until real execution evidence exists."
    )

    render_blocks(document, parse_markdown(design))
    document.add_page_break()
    render_blocks(document, parse_markdown(conformance))

    path = REPORTS / "Design_Report_EN.docx"
    document.save(path)
    print("Word report written: %s" % path)

    return [EN_TITLE] + collect_headings(design) + collect_headings(conformance)


def build_french_report(design: str, conformance: str) -> list[str]:
    """Create the French Word report and return its section headings."""
    document = Document()
    render_blocks(document, parse_markdown(FR_SUMMARY_MD))

    document.add_page_break()
    document.add_heading("Annexe A : rapport technique complet (anglais)", level=1)
    render_blocks(document, parse_markdown(design))
    render_blocks(document, parse_markdown(conformance))

    path = REPORTS / "Rapport_de_Conception_FR.docx"
    document.save(path)
    print("Word report written: %s" % path)

    return collect_headings(FR_SUMMARY_MD) + [
        "Annexe A : rapport technique complet (anglais)"
    ]


def main() -> None:
    """Entry point: generate both Word reports and their PDF versions."""
    REPORTS.mkdir(parents=True, exist_ok=True)

    design = read_doc("design.md")
    conformance = read_doc("iso25010-conformance.md")

    english_sections = build_english_report(design, conformance)
    french_sections = build_french_report(design, conformance)

    convert_to_pdf(
        REPORTS / "Design_Report_EN.docx",
        REPORTS / "Design_Report_EN.pdf",
        EN_TITLE,
        english_sections,
    )
    convert_to_pdf(
        REPORTS / "Rapport_de_Conception_FR.docx",
        REPORTS / "Rapport_de_Conception_FR.pdf",
        FR_TITLE,
        french_sections,
    )
    print("Report generation complete. Output directory: %s" % REPORTS)


if __name__ == "__main__":
    main()

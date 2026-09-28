from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def extract_paragraph(paragraph: Paragraph, index: int, location: str) -> dict:
    """
    Extract one paragraph while preserving run-level formatting.
    """

    text = paragraph.text.strip()

    runs = []

    for run in paragraph.runs:

        if not run.text:
            continue

        runs.append(
            {
                "text": run.text,
                "bold": bool(run.bold)
            }
        )

    return {
        "index": index,
        "text": text,
        "style": paragraph.style.name,
        "runs": runs,
        "location": location
    }


def extract_from_table(
    table: Table,
    paragraphs: list[dict],
    counter: list[int],
    location: str
) -> None:
    """
    Recursively extract paragraphs from a table.
    """

    for row_index, row in enumerate(table.rows):

        for cell_index, cell in enumerate(row.cells):

            cell_location = (
                f"{location}"
                f".row{row_index}"
                f".cell{cell_index}"
            )

            for element in cell._tc.iterchildren():

                # Normal paragraph inside cell
                if element.tag.endswith("}p"):

                    paragraph = Paragraph(
                        element,
                        cell
                    )

                    if not paragraph.text.strip():
                        continue

                    counter[0] += 1

                    paragraphs.append(
                        extract_paragraph(
                            paragraph,
                            counter[0],
                            cell_location
                        )
                    )

                # Nested table inside cell
                elif element.tag.endswith("}tbl"):

                    nested_table = Table(
                        element,
                        cell
                    )

                    extract_from_table(
                        nested_table,
                        paragraphs,
                        counter,
                        f"{cell_location}.table"
                    )


def extract_text(file_path: Path) -> list[dict]:
    """
    Extract paragraphs from the complete DOCX body.

    This includes:
    - normal paragraphs
    - paragraphs inside tables
    - nested tables
    """

    document = Document(file_path)

    paragraphs = []

    counter = [0]

    body = document.element.body

    for element in body.iterchildren():

        # --------------------------------------------------------
        # NORMAL DOCUMENT PARAGRAPH
        # --------------------------------------------------------

        if element.tag.endswith("}p"):

            paragraph = Paragraph(
                element,
                document
            )

            if not paragraph.text.strip():
                continue

            counter[0] += 1

            paragraphs.append(
                extract_paragraph(
                    paragraph,
                    counter[0],
                    "body"
                )
            )

        # --------------------------------------------------------
        # TABLE
        # --------------------------------------------------------

        elif element.tag.endswith("}tbl"):

            table = Table(
                element,
                document
            )

            extract_from_table(
                table,
                paragraphs,
                counter,
                f"table"
            )

    return paragraphs
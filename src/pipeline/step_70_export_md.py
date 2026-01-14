"""Step 70: Export document to Markdown format."""

import logging
from pathlib import Path

from src.schemas.models import Block, Document, Table

logger = logging.getLogger(__name__)


def format_table_markdown(table: Table) -> str:
    """Format table as Markdown."""
    if not table.cells:
        return ""

    # Build grid from cells
    max_row = max(cell.row for cell in table.cells) if table.cells else 0
    max_col = max(cell.col for cell in table.cells) if table.cells else 0

    # Create 2D grid
    grid: list[list[str]] = []
    for r in range(max_row + 1):
        row: list[str] = [""] * (max_col + 1)
        grid.append(row)

    for cell in table.cells:
        if cell.row <= max_row and cell.col <= max_col:
            grid[cell.row][cell.col] = cell.text_raw or ""

    # Build Markdown table
    lines: list[str] = []

    # Header row
    if grid:
        header = "| " + " | ".join(grid[0]) + " |"
        lines.append(header)
        # Separator
        separator = "| " + " | ".join(["---"] * len(grid[0])) + " |"
        lines.append(separator)

        # Data rows
        for row in grid[1:]:
            row_str = "| " + " | ".join(row) + " |"
            lines.append(row_str)

    return "\n".join(lines)


def export_to_markdown(document: Document, output_path: Path) -> None:
    """Export document to Markdown format."""
    logger.info("Exporting document to Markdown...")

    lines: list[str] = []

    # Document header
    lines.append(f"# {document.pdf.filename}")
    lines.append("")
    lines.append(f"*Extracted from PDF with {document.pdf.pages} pages*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Process each page
    for page in document.pages:
        lines.append(f"## Page {page.page_index + 1}")
        lines.append("")

        if page.semantic_section:
            lines.append(f"*Section: {page.semantic_section}*")
            lines.append("")

        # Process items in reading order
        for item in page.items:
            if isinstance(item, Block):
                # Format block based on type
                if item.type.value == "title":
                    lines.append(f"### {item.text}")
                elif item.type.value == "section_header":
                    lines.append(f"#### {item.text}")
                else:
                    # Regular text block
                    lines.append(item.text)

                # Add anchor (format: [#p{page}_b{block}])
                lines.append(f"*[#{item.block_id}]*")
                lines.append("")

            elif isinstance(item, Table):
                # Format table
                table_md = format_table_markdown(item)
                if table_md:
                    lines.append(table_md)
                    lines.append("")
                    # Add anchor (format: [#p{page}_t{table}])
                    lines.append(f"*[#{item.table_id}]*")
                    lines.append("")

        lines.append("---")
        lines.append("")

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Markdown export saved to {output_path}")


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_70_export_md.py <document_json_path>")
        sys.exit(1)

    document_path = Path(sys.argv[1])
    output_path = document_path.parent / "document.md"

    with open(document_path, "r", encoding="utf-8") as f:
        document_dict = json.load(f)

    from src.schemas.models import Document

    document = Document.model_validate(document_dict)
    export_to_markdown(document, output_path)

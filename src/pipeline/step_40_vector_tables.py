"""Step 40: Vector table extraction (Camelot/Tabula for native pages)."""

import json
import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pandas as pd

from src.schemas.models import BBox, Cell, SourceType, Table

logger = logging.getLogger(__name__)


def extract_vector_tables_camelot(pdf_path: Path, page_index: int) -> list[Table]:
    """Extract tables using Camelot (if available)."""
    tables: list[Table] = []

    try:
        import camelot

        # Camelot uses 1-based page numbers
        camelot_tables = camelot.read_pdf(str(pdf_path), pages=str(page_index + 1), flavor="lattice")

        for i, camelot_table in enumerate(camelot_tables):
            df = camelot_table.df

            # Get bounding box from Camelot
            bbox_data = camelot_table._bbox
            bbox = BBox(
                x0=float(bbox_data[0]),
                y0=float(bbox_data[1]),
                x1=float(bbox_data[2]),
                y1=float(bbox_data[3]),
            )

            # Convert DataFrame to cells
            cells: list[Cell] = []
            grid: dict[str, list[str]] = {}

            for row_idx, row in df.iterrows():
                row_cells: list[str] = []
                for col_idx, value in enumerate(row):
                    text_raw = str(value) if pd.notna(value) else ""

                    cell = Cell(
                        row=row_idx,
                        col=col_idx,
                        text_raw=text_raw,
                        value_num=None,  # Will be parsed in normalization step
                        unit=None,
                        bbox=None,
                        confidence=1.0,
                    )
                    cells.append(cell)
                    row_cells.append(text_raw)

                grid[str(col_idx)] = row_cells

            table_id = f"p{page_index}_t{i}"
            table = Table(
                table_id=table_id,
                bbox=bbox,
                source=SourceType.VECTOR,
                confidence=1.0,
                cells=cells,
                grid=grid,
            )

            tables.append(table)

    except ImportError:
        logger.debug("Camelot not available, skipping")
    except Exception as e:
        logger.warning(f"Error extracting tables with Camelot on page {page_index}: {e}")

    return tables


def extract_vector_tables_tabula(pdf_path: Path, page_index: int) -> list[Table]:
    """Extract tables using Tabula (if available)."""
    tables: list[Table] = []

    try:
        import tabula

        # Tabula uses 1-based page numbers
        dfs = tabula.read_pdf(str(pdf_path), pages=page_index + 1, multiple_tables=True)

        for i, df in enumerate(dfs):
            # Tabula doesn't provide bbox directly, estimate from page
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            page_rect = page.rect

            # Simple bbox (full page width, estimate height)
            bbox = BBox(
                x0=0.0,
                y0=float(i * 200),  # Rough estimate
                x1=float(page_rect.width),
                y1=float((i + 1) * 200),
            )

            # Convert DataFrame to cells
            cells: list[Cell] = []
            grid: dict[str, list[str]] = {}

            for row_idx, row in df.iterrows():
                row_cells: list[str] = []
                for col_idx, value in enumerate(row):
                    text_raw = str(value) if pd.notna(value) else ""

                    cell = Cell(
                        row=row_idx,
                        col=col_idx,
                        text_raw=text_raw,
                        value_num=None,
                        unit=None,
                        bbox=None,
                        confidence=1.0,
                    )
                    cells.append(cell)
                    row_cells.append(text_raw)

                grid[str(col_idx)] = row_cells

            table_id = f"p{page_index}_t{i}"
            table = Table(
                table_id=table_id,
                bbox=bbox,
                source=SourceType.VECTOR,
                confidence=0.9,  # Tabula slightly less reliable
                cells=cells,
                grid=grid,
            )

            tables.append(table)

            doc.close()

    except ImportError:
        logger.debug("Tabula not available, skipping")
    except Exception as e:
        logger.warning(f"Error extracting tables with Tabula on page {page_index}: {e}")

    return tables


def extract_vector_tables(pdf_path: Path, page_index: int) -> list[Table]:
    """Extract vector tables using available tools (Camelot preferred, Tabula fallback)."""
    tables: list[Table] = []

    # Try Camelot first
    camelot_tables = extract_vector_tables_camelot(pdf_path, page_index)
    if camelot_tables:
        tables.extend(camelot_tables)
        logger.debug(f"Extracted {len(camelot_tables)} tables with Camelot from page {page_index}")
    else:
        # Fallback to Tabula
        tabula_tables = extract_vector_tables_tabula(pdf_path, page_index)
        if tabula_tables:
            tables.extend(tabula_tables)
            logger.debug(f"Extracted {len(tabula_tables)} tables with Tabula from page {page_index}")

    return tables


def process_vector_tables(
    pdf_path: Path, manifest: dict[str, Any], output_dir: Path
) -> dict[int, list[Table]]:
    """Process vector table extraction for native/mixed pages."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_tables: dict[int, list[Table]] = {}

    pages = manifest.get("pages", [])
    for page_data in pages:
        page_index = page_data["page_index"]
        mode = page_data.get("mode", "native")
        vector_line_density = page_data.get("vector_line_density", 0.0)

        # Extract vector tables for native and mixed pages with table suspicion
        if mode in ("native", "mixed") and vector_line_density > 0.2:
            try:
                tables = extract_vector_tables(pdf_path, page_index)
                all_tables[page_index] = tables

                # Save to JSONL
                output_file = output_dir / "vector_tables.jsonl"
                with open(output_file, "a", encoding="utf-8") as f:
                    for table in tables:
                        f.write(table.model_dump_json() + "\n")

                logger.info(f"Extracted {len(tables)} vector tables from page {page_index}")
            except Exception as e:
                logger.error(f"Error extracting vector tables from page {page_index}: {e}")
                all_tables[page_index] = []

    return all_tables


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python step_40_vector_tables.py <pdf_path> <manifest_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    output_dir = Path("data/10_work/tables_raw")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    process_vector_tables(pdf_path, manifest, output_dir)

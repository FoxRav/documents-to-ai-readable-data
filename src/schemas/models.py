"""Pydantic models for document structure."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PageMode(str, Enum):
    """Page classification mode."""

    NATIVE = "native"
    SCAN = "scan"
    MIXED = "mixed"


class SourceType(str, Enum):
    """Data source type."""

    NATIVE = "native"
    OCR = "ocr"
    VECTOR = "vector"
    MINERU = "mineru"
    DOLPHIN = "dolphin"


class BlockType(str, Enum):
    """Block semantic type (layout-level)."""

    TEXT = "text"
    TITLE = "title"
    SECTION_HEADER = "section_header"
    LIST_ITEM = "list_item"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    PICTURE = "picture"
    # Music sheet types
    MUSIC_STAFF = "music_staff"  # Staff lines with notes
    MUSIC_DYNAMIC = "music_dynamic"  # p, mf, f, ff, pp, etc.
    MUSIC_EXPRESSION = "music_expression"  # rit., a tempo, cresc., etc.
    MUSIC_TEMPO = "music_tempo"  # Tempo marking (♩= 120)
    MUSIC_MEASURE_NUM = "music_measure_num"  # Measure numbers


class ContentType(str, Enum):
    """Document content type classification."""
    
    FINANCIAL = "financial"  # Financial statements
    MUSIC_SHEET = "music_sheet"  # Sheet music / notation
    GENERAL = "general"  # General documents
    TECHNICAL = "technical"  # Technical documents
    LEGAL = "legal"  # Legal documents


class FinancialType(str, Enum):
    """Financial statement type."""

    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW_STATEMENT = "cash_flow_statement"
    CHANGES_IN_EQUITY = "changes_in_equity"
    NOTES = "notes"
    ACCOUNTING_POLICIES = "accounting_policies"
    COMMITMENTS_CONTINGENCIES = "commitments_contingencies"
    RELATED_PARTY = "related_party"
    AUDITORS_REPORT = "auditors_report"
    MANAGEMENT_REPORT = "management_report"
    BUDGET_COMPARISON = "budget_comparison"
    PERFORMANCE_INDICATORS = "performance_indicators"
    APPENDIX = "appendix"


class MusicMetadata(BaseModel):
    """Music sheet metadata."""
    
    title: Optional[str] = Field(None, description="Piece title")
    composer: Optional[str] = Field(None, description="Composer name and dates")
    dedication: Optional[str] = Field(None, description="Dedication text")
    tempo: Optional[str] = Field(None, description="Tempo marking (e.g., ♩= 120)")
    time_signature: Optional[str] = Field(None, description="Time signature (e.g., 4/4)")
    key_signature: Optional[str] = Field(None, description="Key signature")
    instrument: Optional[str] = Field(None, description="Instrument (e.g., guitar)")
    copyright: Optional[str] = Field(None, description="Copyright notice")
    performance_notes: list[str] = Field(default_factory=list, description="Special performance instructions")
    dynamics: list[str] = Field(default_factory=list, description="Dynamic markings found")
    expressions: list[str] = Field(default_factory=list, description="Expression markings found")
    measure_count: Optional[int] = Field(None, description="Number of measures")


class Severity(str, Enum):
    """QA finding severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BBox(BaseModel):
    """Bounding box coordinates."""

    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Top coordinate")
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Bottom coordinate")

    @field_validator("x1")
    @classmethod
    def validate_x1(cls, v: float, info: Any) -> float:
        """Ensure x1 > x0."""
        if "x0" in info.data and v <= info.data["x0"]:
            raise ValueError("x1 must be greater than x0")
        return v

    @field_validator("y1")
    @classmethod
    def validate_y1(cls, v: float, info: Any) -> float:
        """Ensure y1 > y0."""
        if "y0" in info.data and v <= info.data["y0"]:
            raise ValueError("y1 must be greater than y0")
        return v


class FontStats(BaseModel):
    """Font statistics for a text block."""

    size: Optional[float] = None
    family: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None


class Cell(BaseModel):
    """Table cell."""

    row: int = Field(..., ge=0, description="Row index (0-based)")
    col: int = Field(..., ge=0, description="Column index (0-based)")
    text_raw: str = Field(..., description="Raw text content")
    value_num: Optional[float] = Field(None, description="Parsed numeric value")
    unit: Optional[str] = Field(None, description="Unit (e.g., '€', 't€', '%')")
    bbox: Optional[BBox] = Field(None, description="Cell bounding box")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


class Block(BaseModel):
    """Text block."""

    block_id: str = Field(..., description="Unique block identifier")
    type: BlockType = Field(..., description="Block semantic type")
    text: str = Field(..., description="Text content")
    bbox: BBox = Field(..., description="Bounding box")
    source: SourceType = Field(..., description="Data source")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    font_stats: Optional[FontStats] = Field(None, description="Font statistics")
    semantic_type: Optional[str] = Field(None, description="Layout semantic type")
    financial_type: Optional[FinancialType] = Field(None, description="Financial statement type")
    classification_evidence: list[str] = Field(default_factory=list, description="Classification evidence")
    # V8: Adaptive PSM tracking
    ocr_pass_used: Optional[int] = Field(None, description="OCR pass used (1=PSM6, 2=PSM11, 3=PSM4)")
    # V8: TOC target page mapping
    toc_target_page: Optional[int] = Field(None, description="Target page number from TOC entry (document numbering)")
    pdf_target_page: Optional[int] = Field(None, description="Target PDF page index (0-based, after offset applied)")


class Table(BaseModel):
    """Table structure."""

    table_id: str = Field(..., description="Unique table identifier")
    bbox: BBox = Field(..., description="Table bounding box")
    source: SourceType = Field(..., description="Data source")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    cells: list[Cell] = Field(default_factory=list, description="Table cells")
    grid: dict[str, list[str]] = Field(
        default_factory=dict, description="Grid representation (column -> rows)"
    )
    semantic_type: Optional[str] = Field(None, description="Layout semantic type")
    financial_type: Optional[FinancialType] = Field(None, description="Financial statement type")
    classification_evidence: list[str] = Field(default_factory=list, description="Classification evidence")


class Page(BaseModel):
    """Page with extracted content."""

    page_index: int = Field(..., ge=0, description="Page index (0-based)")
    width: float = Field(..., gt=0, description="Page width")
    height: float = Field(..., gt=0, description="Page height")
    mode: Optional[PageMode] = Field(None, description="Page classification mode")
    content_type: Optional[ContentType] = Field(None, description="Document content type")
    semantic_section: Optional[str] = Field(None, description="Semantic section classification")
    semantic_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Classification confidence")
    ocr_quality: Optional[dict[str, Any]] = Field(None, description="OCR quality metrics (V7)")
    music_metadata: Optional[MusicMetadata] = Field(None, description="Music sheet metadata (if music_sheet)")
    items: list[Block | Table] = Field(default_factory=list, description="Page items (blocks and tables)")


class PDFInfo(BaseModel):
    """PDF metadata."""

    filename: str = Field(..., description="PDF filename")
    pages: int = Field(..., gt=0, description="Total page count")


class Document(BaseModel):
    """Complete document structure."""

    pdf: PDFInfo = Field(..., description="PDF metadata")
    pages: list[Page] = Field(default_factory=list, description="Pages")
    # V8: Page number offset (pdf_page_index = toc_page_number + offset)
    page_number_offset: Optional[int] = Field(None, description="Offset from document page numbers to PDF indices")


class Finding(BaseModel):
    """QA finding."""

    checker: str = Field(..., description="Checker name")
    page_index: int = Field(..., ge=0, description="Page index")
    block_id: Optional[str] = Field(None, description="Block ID if applicable")
    table_id: Optional[str] = Field(None, description="Table ID if applicable")
    bbox: Optional[BBox] = Field(None, description="Bounding box if applicable")
    reason: str = Field(..., description="Finding reason")
    severity: Severity = Field(..., description="Severity level")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing")


class TableCellExactness(BaseModel):
    """Table cell exactness metrics."""

    empty_cells_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    unparseable_numbers_percent: Optional[float] = Field(None, ge=0.0, le=100.0)


class SumCheck(BaseModel):
    """Sum consistency check result."""

    page_index: int = Field(..., ge=0)
    table_id: str = Field(..., description="Table identifier")
    row_or_col: str = Field(..., description="Row or column identifier")
    expected: float = Field(..., description="Expected sum")
    actual: float = Field(..., description="Actual sum")
    difference: float = Field(..., description="Difference")
    severity: Severity = Field(..., description="Severity level")


class BalanceCheck(BaseModel):
    """Balance sheet check result."""

    page_index: int = Field(..., ge=0)
    table_id: str = Field(..., description="Table identifier")
    assets: float = Field(..., description="Total assets")
    liabilities: float = Field(..., description="Total liabilities")
    difference: float = Field(..., description="Difference (should be ~0)")
    severity: Severity = Field(..., description="Severity level")


class XRefCheck(BaseModel):
    """Cross-reference check result."""

    reference: str = Field(..., description="Reference text (e.g., 'Liitetieto 5')")
    found_in_main: bool = Field(..., description="Found in main document")
    found_in_notes: bool = Field(..., description="Found in notes section")
    severity: Severity = Field(..., description="Severity level")


class DiffCheck(BaseModel):
    """Diff check between multiple sources."""

    page_index: int = Field(..., ge=0)
    table_id: str = Field(..., description="Table identifier")
    sources: list[str] = Field(..., description="Source identifiers")
    differences: str = Field(..., description="Description of differences")
    severity: Severity = Field(..., description="Severity level")


class QAReport(BaseModel):
    """QA report."""

    pdf: PDFInfo = Field(..., description="PDF metadata")
    schema_valid: bool = Field(..., description="Schema validation result")
    table_cell_exactness: Optional[TableCellExactness] = Field(None, description="Cell exactness metrics")
    sum_checks: list[SumCheck] = Field(default_factory=list, description="Sum consistency checks")
    balance_checks: list[BalanceCheck] = Field(default_factory=list, description="Balance sheet checks")
    xref_checks: list[XRefCheck] = Field(default_factory=list, description="Cross-reference checks")
    diff_checks: list[DiffCheck] = Field(default_factory=list, description="Diff checks")
    findings: list[Finding] = Field(default_factory=list, description="All findings")

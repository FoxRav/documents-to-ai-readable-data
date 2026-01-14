"""Main pipeline runner - orchestrates all steps."""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.pipeline.config import get_settings
from src.pipeline.step_00_pdf_probe import probe_pdf
from src.pipeline.step_01_prepare_assets import prepare_assets
from src.pipeline.step_10_native_text import process_native_pages
from src.pipeline.step_20_render_pages import render_pages
from src.pipeline.step_30_layout_regions import process_rendered_pages
from src.pipeline.step_40_vector_tables import process_vector_tables
from src.pipeline.step_41_ocr_tables import process_ocr_tables
from src.pipeline.step_50_merge_reading_order import merge_document
from src.pipeline.step_55_semantic_classify import classify_document
from src.pipeline.step_60_normalize_validate import normalize_and_validate
from src.pipeline.step_70_export_md import export_to_markdown

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    if log_format == "json":
        # JSON logging (structured)
        import json as json_lib

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json_lib.dumps(log_entry)

        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logging.basicConfig(level=level, handlers=[handler])
    else:
        # Text logging
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def run_pipeline(
    pdf_path: Path,
    work_dir: Path,
    out_dir: Path,
    prepare_assets_flag: bool = False,
    model_dir: Path | None = None,
    cache_dir: Path | None = None,
    max_pages: int | None = None,
) -> None:
    """Run the complete pipeline."""
    logger.info(f"Starting pipeline for PDF: {pdf_path}")
    
    # Log GPU status at start
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"🚀 GPU AVAILABLE: {gpu_name} ({vram_gb:.1f} GB VRAM)")
            logger.info("✅ Pipeline will use CUDA for GPU-accelerated operations")
        else:
            logger.warning("⚠️ CUDA not available - pipeline will use CPU (slower)")
    except ImportError:
        logger.warning("⚠️ PyTorch not available - GPU acceleration disabled")

    settings = get_settings()

    # Override model/cache dirs if provided
    if model_dir:
        settings.model_dir = model_dir
    if cache_dir:
        settings.cache_dir = cache_dir

    # Step 01: Prepare assets (if requested)
    if prepare_assets_flag:
        logger.info("Step 01: Preparing assets...")
        debug_dir = work_dir / "debug"
        prepare_assets(work_dir, debug_dir)

    # Step 00: PDF Probe & Route
    logger.info("Step 00: Probing PDF and generating manifest...")
    manifest_dir = work_dir / "page_manifest"
    manifest = probe_pdf(pdf_path, manifest_dir, max_pages=max_pages)
    manifest_path = manifest_dir / "manifest.json"
    
    # Note: max_pages is already handled in probe_pdf, but log it here for clarity
    if max_pages is not None:
        processed_pages = len(manifest.get("pages", []))
        total_pages = manifest.get("pdf", {}).get("total_pages", processed_pages)
        logger.info(f"Processing limited to first {processed_pages} pages (out of {total_pages} total)")

    # Step 10: Native text extraction
    logger.info("Step 10: Extracting native text...")
    blocks_native_dir = work_dir / "blocks_native"
    all_blocks = process_native_pages(pdf_path, manifest, blocks_native_dir)

    # Step 20: Render pages (scan/mixed)
    logger.info("Step 20: Rendering pages...")
    pages_png_dir = work_dir / "pages_png"
    
    # Check if pages are already rendered
    existing_pages = {i: pages_png_dir / f"page_{i:04d}.png" 
                     for i in range(manifest.get("pdf", {}).get("pages", 0))
                     if (pages_png_dir / f"page_{i:04d}.png").exists()}
    
    if len(existing_pages) == manifest.get("pdf", {}).get("pages", 0):
        logger.info(f"Using {len(existing_pages)} already rendered pages")
        rendered_pages = existing_pages
    else:
        rendered_pages = render_pages(pdf_path, manifest, pages_png_dir)

    # Step 30: Layout region detection
    logger.info("Step 30: Detecting layout regions...")
    regions_dir = work_dir / "regions"
    
    # Check CUDA availability for logging
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB)")
    except ImportError:
        pass
    
    all_regions = process_rendered_pages(rendered_pages, regions_dir)

    # Step 40: Vector tables
    logger.info("Step 40: Extracting vector tables...")
    tables_raw_dir = work_dir / "tables_raw"
    all_vector_tables = process_vector_tables(pdf_path, manifest, tables_raw_dir)

    # Step 41: OCR tables + OCR text regions (with CUDA if available)
    logger.info("Step 41: Extracting OCR tables and text with PaddleOCR PP-StructureV3...")
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"Using CUDA for OCR: {torch.cuda.get_device_name(0)}")
    except ImportError:
        logger.warning("PyTorch not available, OCR will use CPU")
    
    # V2: Guardrail - check if all pages are scan
    pages = manifest.get("pages", [])
    all_scan = all(p.get("mode") == "scan" for p in pages)
    if all_scan and len(pages) > 0:
        logger.warning("⚠️ All pages classified as 'scan' - ensuring Step 41B (OCR text) runs for all pages")
    
    debug_dir = work_dir / "debug"
    all_ocr_tables, all_ocr_blocks = process_ocr_tables(rendered_pages, all_regions, tables_raw_dir, debug_dir)

    # V2: Ensure OCR blocks are saved
    blocks_ocr_dir = work_dir / "blocks_ocr"
    blocks_ocr_dir.mkdir(parents=True, exist_ok=True)
    for page_idx, ocr_blocks in all_ocr_blocks.items():
        output_file = blocks_ocr_dir / f"page_{page_idx:04d}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for block in ocr_blocks:
                f.write(block.model_dump_json() + "\n")

    # Combine all tables
    all_tables: dict[int, list] = {}
    for page_idx in set(list(all_vector_tables.keys()) + list(all_ocr_tables.keys())):
        all_tables[page_idx] = (
            all_vector_tables.get(page_idx, []) + all_ocr_tables.get(page_idx, [])
        )

    # Combine all blocks (native + OCR)
    for page_idx, ocr_blocks in all_ocr_blocks.items():
        if page_idx not in all_blocks:
            all_blocks[page_idx] = []
        all_blocks[page_idx].extend(ocr_blocks)
    
    # V2: Validation - ensure we have data
    total_blocks = sum(len(blocks) for blocks in all_blocks.values())
    total_tables = sum(len(tables) for tables in all_tables.values())
    logger.info(f"V2 validation: {total_blocks} blocks, {total_tables} tables extracted")
    if total_blocks == 0 and total_tables == 0:
        logger.error("❌ CRITICAL: No data extracted! document.json will be empty. Check Step 41.")

    # V6 Gate B: Refine block types (TOC detection, table validation)
    logger.info("V6 Gate B: Refining block types (TOC detection, table validation)...")
    from src.normalize.block_type_refine import refine_block_types
    
    pages_data = manifest.get("pages", [])
    all_tables, all_blocks = refine_block_types(pages_data, all_tables, all_blocks)
    
    refined_total_blocks = sum(len(blocks) for blocks in all_blocks.values())
    refined_total_tables = sum(len(tables) for tables in all_tables.values())
    logger.info(f"V6 Gate B: After refinement: {refined_total_blocks} blocks, {refined_total_tables} tables")

    # V7 Gate A: Calculate OCR quality metrics
    logger.info("V7 Gate A: Calculating OCR quality metrics...")
    from src.pipeline.step_42_ocr_quality import process_page_ocr_quality, apply_noise_gate
    
    ocr_quality_metrics: dict[int, dict[str, Any]] = {}
    debug_dir = work_dir / "debug"
    bad_quality_pages: list[int] = []
    
    # Collect OCR text from blocks for quality analysis
    for page_idx, blocks in all_blocks.items():
        ocr_text = " ".join([block.text for block in blocks if hasattr(block, "text")])
        if ocr_text:
            quality_metrics = process_page_ocr_quality(page_idx, ocr_text, debug_dir)
            ocr_quality_metrics[page_idx] = quality_metrics
            
            # V7: Apply noise gate
            if apply_noise_gate(quality_metrics):
                bad_quality_pages.append(page_idx)
                logger.warning(
                    f"Page {page_idx}: OCR quality is bad (status={quality_metrics.get('status')}, "
                    f"repeat_run_max={quality_metrics.get('repeat_run_max')})"
                )
    
    # V8 Gate B: Full-run quality gate
    total_pages = len(manifest.get("pages", []))
    if total_pages > 0:
        bad_ratio = len(bad_quality_pages) / total_pages
        strict_threshold = 0.10  # 10%
        lenient_threshold = 0.20  # 20%
        
        logger.info(f"V8 Gate B: Quality gate check - {len(bad_quality_pages)}/{total_pages} pages with bad OCR ({bad_ratio:.1%})")
        
        if bad_ratio > lenient_threshold:
            logger.error(
                f"⚠️ V8 Quality Gate FAILED: {bad_ratio:.1%} pages have bad OCR quality (> {lenient_threshold:.0%} threshold). "
                f"Bad pages: {bad_quality_pages[:10]}{'...' if len(bad_quality_pages) > 10 else ''}"
            )
        elif bad_ratio > strict_threshold:
            logger.warning(
                f"V8 Quality Gate WARNING: {bad_ratio:.1%} pages have bad OCR quality (> {strict_threshold:.0%} strict threshold). "
                f"Pipeline continues but results may be degraded."
            )
        else:
            logger.info(f"✅ V8 Quality Gate PASSED: {bad_ratio:.1%} bad pages (< {strict_threshold:.0%} threshold)")

    # Step 50: Merge & Reading Order
    logger.info("Step 50: Merging elements and establishing reading order...")
    document = merge_document(manifest, all_blocks, all_tables, ocr_quality_metrics)

    # Step 55: Semantic classification
    logger.info("Step 55: Applying semantic classification...")
    document = classify_document(document)

    # Step 60: Normalize & Validate
    logger.info("Step 60: Normalizing and validating...")
    normalized_doc, qa_report = normalize_and_validate(document, out_dir)

    # Step 70: Export to Markdown
    logger.info("Step 70: Exporting to Markdown...")
    md_path = out_dir / "document.md"
    export_to_markdown(normalized_doc, md_path)

    logger.info("Pipeline completed successfully!")
    logger.info(f"Output files:")
    logger.info(f"  - Document JSON: {out_dir / 'document.json'}")
    logger.info(f"  - Document MD: {md_path}")
    logger.info(f"  - QA Report: {out_dir / 'qa_report.json'}")


def run_image_pipeline(
    image_path: Path,
    out_dir: Path,
) -> None:
    """
    Run image processing pipeline.
    
    Routes to music sheet or document processing based on content detection.
    """
    from src.music.detect import detect_music_sheet_from_path
    from src.music.extract import process_music_sheet
    
    logger.info(f"Processing image: {image_path}")
    
    # Detect content type
    is_music, confidence, detection_info = detect_music_sheet_from_path(image_path)
    
    if is_music:
        logger.info(f"Detected music sheet (confidence: {confidence:.0%})")
        result = process_music_sheet(image_path, run_omr=True)
        
        # Create music output directory
        music_dir = out_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        
        # Save music.json
        music_json_path = music_dir / "music.json"
        with open(music_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved: {music_json_path}")
        
        # Save music.md (markdown)
        from tools.process_image import format_as_markdown
        music_md_path = music_dir / "music.md"
        with open(music_md_path, "w", encoding="utf-8") as f:
            f.write(format_as_markdown(result))
        logger.info(f"Saved: {music_md_path}")
        
        # If OMR succeeded, the MusicXML is already in omr_output/
        omr_result = result.get("omr", {})
        if omr_result.get("success") and omr_result.get("musicxml_path"):
            import shutil
            src_xml = Path(omr_result["musicxml_path"])
            if src_xml.exists():
                dst_xml = music_dir / "music.xml"
                shutil.copy(src_xml, dst_xml)
                logger.info(f"Saved: {dst_xml}")
        
        # QA summary
        qa = result.get("qa", {})
        logger.info(f"QA Status: {qa.get('status', 'unknown').upper()}")
        for finding in qa.get("findings", []):
            logger.info(f"  - [{finding.get('severity')}] {finding.get('message')}")
    
    else:
        # TODO: General document image processing (OCR)
        logger.warning(f"Image is not a music sheet (confidence: {confidence:.0%})")
        logger.warning("General document image processing not yet implemented")
        
        # Save detection info anyway
        out_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "input": str(image_path),
            "is_music_sheet": False,
            "confidence": confidence,
            "detection_info": detection_info,
        }
        with open(out_dir / "document.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PDF-tyyppireititin pipeline - processes PDFs and images to structured data"
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", type=Path, help="Path to input PDF file")
    input_group.add_argument("--image", type=Path, help="Path to input image file (JPG/PNG)")
    
    parser.add_argument(
        "--prepare-assets",
        action="store_true",
        help="Prepare models and assets before processing",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help="Model directory (default: ./models)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory (default: ./cache)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("data/10_work"),
        help="Work directory (default: data/10_work)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: same as input file directory)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--log-format",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Logging format",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit processing to first N pages (for testing, PDF only)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_format)

    # Determine input path and output directory
    if args.pdf:
        input_path = args.pdf
        default_out_dir = Path("out")
    else:
        input_path = args.image
        default_out_dir = input_path.parent  # Same folder as input
    
    out_dir = args.out_dir or default_out_dir
    
    # Validate input path
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Create directories
    args.work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.pdf:
            # PDF pipeline
            run_pipeline(
                pdf_path=args.pdf,
                work_dir=args.work_dir,
                out_dir=out_dir,
                prepare_assets_flag=args.prepare_assets,
                model_dir=args.model_dir,
                cache_dir=args.cache_dir,
                max_pages=args.max_pages,
            )
        else:
            # Image pipeline
            run_image_pipeline(
                image_path=args.image,
                out_dir=out_dir,
            )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

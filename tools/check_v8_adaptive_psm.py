#!/usr/bin/env python3
"""Check V8 adaptive PSM results."""

import json
from pathlib import Path


def main() -> None:
    """Check adaptive PSM results."""
    doc_path = Path("out/document.json")
    
    if not doc_path.exists():
        print("Error: out/document.json not found")
        return
    
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    print("=== V8 ADAPTIVE PSM RESULTS ===\n")
    
    # Check ocr_pass_used per page
    for page in doc.get("pages", []):
        page_idx = page.get("page_index", 0)
        items = page.get("items", [])
        
        # Count passes used
        pass_counts: dict[int, int] = {}
        items_with_pass: int = 0
        
        for item in items:
            ocr_pass = item.get("ocr_pass_used")
            if ocr_pass is not None:
                items_with_pass += 1
                pass_counts[ocr_pass] = pass_counts.get(ocr_pass, 0) + 1
        
        # Get OCR quality
        ocr_quality = page.get("ocr_quality", {})
        status = ocr_quality.get("status", "unknown")
        score = ocr_quality.get("score", 0)
        repeat_run = ocr_quality.get("repeat_run_max", 0)
        
        print(f"Page {page_idx}: {len(items)} items, {items_with_pass} with ocr_pass_used")
        print(f"  OCR quality: status={status}, score={score:.2f}, repeat_run_max={repeat_run}")
        if pass_counts:
            print(f"  Pass counts: {pass_counts}")
        else:
            print("  No OCR pass info (items may not be from Tesseract)")
        print()
    
    # Summary
    total_items = sum(len(p.get("items", [])) for p in doc.get("pages", []))
    total_with_pass = sum(
        1 for p in doc.get("pages", [])
        for i in p.get("items", [])
        if i.get("ocr_pass_used") is not None
    )
    
    print(f"=== SUMMARY ===")
    print(f"Total items: {total_items}")
    print(f"Items with ocr_pass_used: {total_with_pass}")
    
    # Check for multi-pass usage
    multi_pass_items = sum(
        1 for p in doc.get("pages", [])
        for i in p.get("items", [])
        if i.get("ocr_pass_used") is not None and i.get("ocr_pass_used") > 1
    )
    print(f"Items using pass 2 or 3 (adaptive): {multi_pass_items}")


if __name__ == "__main__":
    main()

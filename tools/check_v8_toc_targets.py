#!/usr/bin/env python3
"""Check V8 TOC target page parsing results."""

import json
from pathlib import Path


def main() -> None:
    """Check TOC target page results."""
    doc_path = Path("out/document.json")
    
    if not doc_path.exists():
        print("Error: out/document.json not found")
        return
    
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    # V8: Show page offset
    page_offset = doc.get("page_number_offset", "N/A")
    print(f"=== V8 PAGE NUMBER OFFSET: {page_offset} ===\n")
    
    print("=== V8 TOC TARGET PAGES ===\n")
    
    # Find TOC pages and check target pages
    for page in doc.get("pages", []):
        page_idx = page.get("page_index", 0)
        section = page.get("semantic_section", "")
        
        if section != "toc":
            continue
        
        print(f"Page {page_idx} (TOC):")
        
        items = page.get("items", [])
        items_with_target = 0
        
        for item in items:
            target_page = item.get("toc_target_page")
            pdf_target = item.get("pdf_target_page")
            financial_type = item.get("financial_type")
            text = item.get("text", "")[:50]
            
            if target_page is not None or financial_type is not None:
                items_with_target += 1
                print(f"  - TOC: {target_page} -> PDF: {pdf_target}, Type: {financial_type}")
                print(f"    Text: {text}...")
        
        print(f"  Total items with target_page or financial_type: {items_with_target}/{len(items)}\n")
    
    # Summary
    total_with_target = sum(
        1 for p in doc.get("pages", [])
        for i in p.get("items", [])
        if i.get("toc_target_page") is not None
    )
    total_with_pdf_target = sum(
        1 for p in doc.get("pages", [])
        for i in p.get("items", [])
        if i.get("pdf_target_page") is not None
    )
    total_with_financial_type = sum(
        1 for p in doc.get("pages", [])
        for i in p.get("items", [])
        if i.get("financial_type") is not None
    )
    
    print(f"=== SUMMARY ===")
    print(f"Page number offset: {page_offset}")
    print(f"Items with toc_target_page: {total_with_target}")
    print(f"Items with pdf_target_page: {total_with_pdf_target}")
    print(f"Items with financial_type: {total_with_financial_type}")


if __name__ == "__main__":
    main()

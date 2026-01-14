"""Check V7 test results."""

import json
from pathlib import Path


def main() -> None:
    """Check V7 test results."""
    doc_path = Path("out/document.json")
    qa_path = Path("out/qa_report.json")
    
    if not doc_path.exists():
        print("❌ document.json not found")
        return
    
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    print("=== V7 TEST RESULTS ===")
    print(f"Pages: {len(doc['pages'])}")
    print(f"Pages with semantic_section: {sum(1 for p in doc['pages'] if p.get('semantic_section'))}")
    print(f"Pages with ocr_quality: {sum(1 for p in doc['pages'] if p.get('ocr_quality'))}")
    print(f"Items with financial_type: {sum(1 for p in doc['pages'] for item in p.get('items', []) if item.get('financial_type'))}")
    print(f"Total items: {sum(len(p.get('items', [])) for p in doc['pages'])}")
    print()
    
    print("=== SEMANTIC SECTIONS ===")
    for i, page in enumerate(doc['pages']):
        section = page.get('semantic_section', 'null')
        confidence = page.get('semantic_confidence', 0)
        print(f"Page {i}: {section} (confidence: {confidence:.2f})")
    print()
    
    print("=== OCR QUALITY (V7 Gate A) ===")
    for i, page in enumerate(doc['pages']):
        quality = page.get('ocr_quality')
        if quality:
            status = quality.get('status', 'N/A')
            score = quality.get('score', 0)
            repeat_run = quality.get('repeat_run_max', 0)
            print(f"Page {i}: status={status}, score={score:.2f}, repeat_run_max={repeat_run}")
    print()
    
    print("=== FINANCIAL TYPES (V7 Gate C) ===")
    financial_types = {}
    for page in doc['pages']:
        for item in page.get('items', []):
            ft = item.get('financial_type')
            if ft:
                financial_types[ft] = financial_types.get(ft, 0) + 1
    
    if financial_types:
        for k, v in sorted(financial_types.items()):
            print(f"  {k}: {v}")
    else:
        print("  No financial_type found")
    print()
    
    print("=== TOC DETECTION (V7 Gate B) ===")
    toc_pages = [i for i, p in enumerate(doc['pages']) if p.get('semantic_section') == 'toc']
    if toc_pages:
        print(f"TOC pages found: {toc_pages}")
        for page_idx in toc_pages:
            page = doc['pages'][page_idx]
            items = page.get('items', [])
            print(f"  Page {page_idx}: {len(items)} items")
            # Check if TOC is table or list_items
            table_count = sum(1 for item in items if item.get('semantic_type') == 'table')
            list_item_count = sum(1 for item in items if item.get('semantic_type') == 'list_item')
            print(f"    Tables: {table_count}, List items: {list_item_count}")
    else:
        print("  No TOC pages detected")
    print()
    
    if qa_path.exists():
        with open(qa_path, "r", encoding="utf-8") as f:
            qa = json.load(f)
        
        print("=== QA REPORT (V7 Gate D) ===")
        findings = qa.get('findings', [])
        print(f"Total findings: {len(findings)}")
        
        by_checker = {}
        for finding in findings:
            checker = finding.get('checker', 'unknown')
            by_checker[checker] = by_checker.get(checker, 0) + 1
        
        for checker, count in sorted(by_checker.items()):
            print(f"  {checker}: {count} findings")
        
        print()
        print("Sample findings:")
        for finding in findings[:5]:
            checker = finding.get('checker', 'unknown')
            reason = finding.get('reason', '')[:80]
            print(f"  {checker}: {reason}...")


if __name__ == "__main__":
    main()

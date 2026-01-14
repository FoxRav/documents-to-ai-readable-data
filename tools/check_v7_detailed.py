"""Detailed V7 check."""

import json
from pathlib import Path


def main() -> None:
    """Check V7 results in detail."""
    doc_path = Path("out/document.json")
    
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    print("=== PAGE 2 DETAILED CHECK ===")
    page2 = doc['pages'][2]
    print(f"Page 2 semantic_section: {page2.get('semantic_section')}")
    print(f"Page 2 items: {len(page2.get('items', []))}")
    
    if page2.get('items'):
        print("Items:")
        for item in page2['items']:
            if 'table_id' in item:
                print(f"  Table: {item.get('table_id')}, cells: {len(item.get('cells', []))}")
            elif 'block_id' in item:
                print(f"  Block: {item.get('block_id')}, type: {item.get('type')}, semantic_type: {item.get('semantic_type')}")
                print(f"    Text: {item.get('text', '')[:100]}")
    
    print()
    print("=== CHECKING BLOCKS_OCR ===")
    blocks_dir = Path("data/10_work/blocks_ocr")
    if blocks_dir.exists():
        page2_blocks = blocks_dir / "page_0002.jsonl"
        if page2_blocks.exists():
            with open(page2_blocks, "r", encoding="utf-8") as f:
                lines = f.readlines()
            print(f"Page 2 OCR blocks file: {len(lines)} lines")
            if lines:
                first_block = json.loads(lines[0])
                print(f"  First block: {first_block.get('block_id')}, text: {first_block.get('text', '')[:100]}")
        else:
            print("Page 2 OCR blocks file not found")


if __name__ == "__main__":
    main()

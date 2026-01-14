"""Check Page 2 details."""

import json
from pathlib import Path


def main() -> None:
    """Check Page 2."""
    # Check OCR blocks
    blocks_file = Path("data/10_work/blocks_ocr/page_0002.jsonl")
    if blocks_file.exists():
        with open(blocks_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"Page 2 OCR blocks file: {len(lines)} lines")
        if lines:
            block = json.loads(lines[0])
            print(f"  Block ID: {block.get('block_id')}")
            print(f"  Text (first 300 chars): {block.get('text', '')[:300]}")
    
    # Check document.json
    doc_path = Path("out/document.json")
    if doc_path.exists():
        with open(doc_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        page2 = doc['pages'][2]
        print(f"\nPage 2 in document.json:")
        print(f"  Items: {len(page2.get('items', []))}")
        print(f"  Semantic section: {page2.get('semantic_section')}")
        
        if page2.get('items'):
            for item in page2['items']:
                if 'block_id' in item:
                    print(f"    Block: {item.get('block_id')}, text: {item.get('text', '')[:100]}")


if __name__ == "__main__":
    main()

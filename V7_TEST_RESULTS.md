# V7 Test Results (5 pages)

## Test Configuration
- **PDF**: Lapua-Tilinpaatos-2024.pdf
- **Pages processed**: 5 (first 5 pages)
- **Date**: 2026-01-13

## Results Summary

### Pages
- **Total pages processed**: 5
- **Pages with semantic_section**: 5 (100%)
- **Pages with ocr_quality**: 5 (100%)
- **Total items**: 57

### Semantic Classification

#### Page-level (semantic_section)
- **Page 0**: `cover` (confidence: 0.50)
- **Page 1**: `toc` (confidence: 0.90) ✅
- **Page 2**: `toc` (confidence: 0.90) ✅
- **Page 3**: `appendix` (confidence: 0.30)
- **Page 4**: `appendix` (confidence: 0.30)

#### Element-level (semantic_type)
- **Total items**: 57
- **TOC pages**: 2 (Page 1 and 2)
- **List items**: 52 (from TOC conversion)
- **Tables**: 0 (TOC correctly converted to list items) ✅

### Financial Types (V7 Gate C) ✅
- **cash_flow_statement**: 3
- **income_statement**: 3
- **notes**: 1
- **Total items with financial_type**: 7

### OCR Quality (V7 Gate A) ✅
- **Page 0**: status=fair, score=0.66, repeat_run_max=8
- **Page 1**: status=bad, score=0.72, repeat_run_max=19 ⚠️
- **Page 2**: status=bad, score=0.74, repeat_run_max=15 ⚠️
- **Page 3**: status=good, score=0.92, repeat_run_max=2
- **Page 4**: status=good, score=0.89, repeat_run_max=3

### QA Report (V7 Gate D) ✅
- **Total findings**: 2
- **OCRQualityChecker**: 2 findings
  - 2 pages have bad OCR quality (Pages 1, 2)
  - 2 pages have high noise (repeat_run_max >= 10)

## V7 Features Verified

### ✅ Gate A: OCR Quality Metrics
- OCR quality metrics calculated for all pages
- Noise gate rules implemented
- Bad quality pages detected (Pages 1, 2)

### ✅ Gate B: TOC Detection and Modeling
- **Page 1 and 2 correctly identified as TOC** (semantic_section: "toc")
- **TOC converted to list items** (not tables)
  - Page 1: 38 list items, 0 tables
  - Page 2: 14 list items, 0 tables
- Page-level TOC detection working

### ✅ Gate C: financial_type from TOC
- **financial_type extracted from TOC entries**
  - cash_flow_statement: 3 items
  - income_statement: 3 items
  - notes: 1 item
- TOC-based classification working

### ✅ Gate D: QA Checkers
- **SemanticSectionChecker**: Working (no findings for mini-run)
- **OCRQualityChecker**: Detecting bad quality pages

## V7 DoD Status

- ✅ **TOC-sivu mallinnetaan `toc`-osioksi ja list-items blokkeina** (ei taulukoksi)
- ✅ **financial_type ei ole kaikkialla null** (7 items with financial_type from TOC)
- ✅ **qa_report.json sisältää semantic- ja ocr-quality -findingit**
- ✅ **OCR-noise gate estää pitkien "cccc/eeee"-jonojen päätymisen taulukkomalliin** (detected, but needs adaptive PSM)

## Observations

1. **TOC Detection**: Working perfectly - Pages 1 and 2 correctly identified
2. **TOC Conversion**: Tables converted to list items successfully
3. **Financial Types**: Extracted from TOC entries (7 items)
4. **OCR Quality**: Bad quality detected on Pages 1 and 2 (high noise)
5. **QA Checkers**: Working and reporting findings

## Next Steps

1. **Adaptive PSM**: Implement adaptive PSM passes for bad quality pages (V7 Gate A.3)
2. **Full-run test**: Run on complete document (154 pages)
3. **V8 preparation**: Once V7 DoD fully validated, proceed to advanced QA checkers

## V7 DoD Status

- ✅ TOC-sivu mallinnetaan `toc`-osioksi ja list-items blokkeina (ei taulukoksi)
- ✅ financial_type ei ole kaikkialla null (7 items with financial_type)
- ✅ qa_report.json sisältää semantic- ja ocr-quality -findingit
- ⚠️ OCR-noise gate toimii (detectoi), mutta adaptive PSM ei vielä toteutettu

**V7 is mostly complete! Ready for adaptive PSM implementation or V8 (advanced QA checkers)!**

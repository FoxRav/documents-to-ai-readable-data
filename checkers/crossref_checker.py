"""Cross-reference checker for notes (V8 Gate D)."""

import re
from typing import Optional

from checkers.base import BaseChecker
from src.schemas.models import Block, Document, Finding, Severity, XRefCheck


class CrossRefChecker(BaseChecker):
    """
    Checks that cross-references (e.g., "Liite 5", "Note 3") exist in the notes section.
    
    For Finnish municipal reports:
    - "Liite X" or "Liitetieto X" should have corresponding note
    """

    @property
    def name(self) -> str:
        """Checker name."""
        return "CrossRefChecker"

    def extract_references(self, text: str) -> list[tuple[str, int]]:
        """
        Extract note references from text.
        
        Returns:
            List of (reference_text, note_number) tuples
        """
        references: list[tuple[str, int]] = []
        
        # Finnish patterns
        finnish_patterns = [
            r"liite\s*(\d+)",
            r"liitetieto\s*(\d+)",
            r"ks\.\s*liite\s*(\d+)",  # "ks. liite" = "see note"
        ]
        
        # English patterns
        english_patterns = [
            r"note\s*(\d+)",
            r"see\s+note\s*(\d+)",
        ]
        
        text_lower = text.lower()
        
        for pattern in finnish_patterns + english_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                ref_text = match.group(0)
                try:
                    note_num = int(match.group(1))
                    references.append((ref_text, note_num))
                except ValueError:
                    continue
        
        return references

    def find_notes_section_numbers(self, document: Document) -> set[int]:
        """
        Find all note numbers that exist in the notes section.
        
        Returns:
            Set of note numbers found
        """
        note_numbers: set[int] = set()
        
        for page in document.pages:
            # Only check pages in notes section
            if page.semantic_section != "notes":
                continue
            
            for item in page.items:
                if isinstance(item, Block):
                    text = item.text.lower()
                    
                    # Look for note headers (e.g., "Liite 5" or "5. Liitetiedot")
                    # Pattern: standalone number at start of line or after "Liite"
                    patterns = [
                        r"^(\d+)\.",  # "5. Something"
                        r"liite\s*(\d+)",
                        r"liitetieto\s*(\d+)",
                        r"note\s*(\d+)",
                    ]
                    
                    for pattern in patterns:
                        matches = re.finditer(pattern, text)
                        for match in matches:
                            try:
                                note_num = int(match.group(1))
                                note_numbers.add(note_num)
                            except ValueError:
                                continue
        
        return note_numbers

    def check(self, document: Document) -> list[Finding]:
        """Check that all cross-references have corresponding notes."""
        findings: list[Finding] = []
        
        # Find all note numbers in notes section
        existing_notes = self.find_notes_section_numbers(document)
        
        if not existing_notes:
            # No notes section found, skip cross-reference check
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason="No notes section found in document - cross-reference check skipped",
                    severity=Severity.INFO,
                )
            )
            return findings
        
        # Collect all references from non-notes sections
        all_references: dict[int, list[tuple[int, str]]] = {}  # note_num -> [(page_idx, ref_text)]
        
        for page in document.pages:
            # Skip notes section (references within notes are fine)
            if page.semantic_section == "notes":
                continue
            
            for item in page.items:
                if isinstance(item, Block):
                    refs = self.extract_references(item.text)
                    for ref_text, note_num in refs:
                        if note_num not in all_references:
                            all_references[note_num] = []
                        all_references[note_num].append((page.page_index, ref_text))
        
        # Check each reference
        missing_notes: set[int] = set()
        
        for note_num, refs in all_references.items():
            if note_num not in existing_notes:
                missing_notes.add(note_num)
                
                # Report first occurrence
                first_page, first_ref = refs[0]
                findings.append(
                    Finding(
                        checker=self.name,
                        page_index=first_page,
                        reason=(
                            f"Cross-reference '{first_ref}' (note {note_num}) not found in notes section. "
                            f"Referenced {len(refs)} time(s) in document."
                        ),
                        severity=Severity.WARNING,
                    )
                )
        
        # Summary finding
        if all_references:
            found_count = len(all_references) - len(missing_notes)
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason=(
                        f"Cross-reference summary: {found_count}/{len(all_references)} references validated. "
                        f"Missing: {sorted(missing_notes) if missing_notes else 'none'}"
                    ),
                    severity=Severity.INFO,
                )
            )
        
        return findings

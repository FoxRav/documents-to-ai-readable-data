"""Unit tests for loc_counter.py"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from loc_counter import (
    count_lines,
    count_lines_c_style,
    count_lines_html_xml_style,
    count_lines_no_comments,
    count_lines_python_style,
    count_lines_sql_style,
    get_category,
    get_language,
    scan_directory,
    should_exclude_path,
)


def test_get_language() -> None:
    """Test language detection."""
    assert get_language(Path("test.py")) == "Python"
    assert get_language(Path("test.js")) == "JavaScript"
    assert get_language(Path("test.ts")) == "TypeScript"
    assert get_language(Path("test.json")) == "JSON"
    assert get_language(Path("test.md")) == "Markdown"
    assert get_language(Path("test.unknown")) == "Other"


def test_get_category() -> None:
    """Test category detection."""
    assert get_category("JSON") == "data"
    assert get_category("Markdown") == "docs"
    assert get_category("Python") == "code"
    assert get_category("XML") == "data"
    assert get_category("HTML") == "code"


def test_count_lines_python_style() -> None:
    """Test Python-style comment counting."""
    test_file = Path(__file__).parent / "fixture_small" / "test.py"
    if not test_file.exists():
        skip("Fixture file not found")

    code, comments, blanks = count_lines_python_style(test_file)
    assert code >= 3  # At least function definition and print
    assert comments >= 2  # At least 2 comment lines
    assert blanks >= 1  # At least 1 blank line


def test_count_lines_c_style() -> None:
    """Test C-style comment counting."""
    test_file = Path(__file__).parent / "fixture_small" / "test.js"
    if not test_file.exists():
        skip("Fixture file not found")

    code, comments, blanks = count_lines_c_style(test_file)
    assert code >= 2  # At least function definition and return
    assert comments >= 3  # At least 3 comment lines
    assert blanks >= 1  # At least 1 blank line


def test_count_lines_sql_style() -> None:
    """Test SQL-style comment counting."""
    test_file = Path(__file__).parent / "fixture_small" / "test.sql"
    if not test_file.exists():
        skip("Fixture file not found")

    code, comments, blanks = count_lines_sql_style(test_file)
    assert code >= 2  # At least 2 SQL statements
    assert comments >= 3  # At least 3 comment lines
    assert blanks >= 0  # Blank lines (may be 0)


def test_count_lines_html_xml_style() -> None:
    """Test HTML/XML-style comment counting."""
    test_file = Path(__file__).parent / "fixture_small" / "test.html"
    if not test_file.exists():
        skip("Fixture file not found")

    code, comments, blanks = count_lines_html_xml_style(test_file)
    assert code >= 5  # At least HTML tags
    assert comments >= 2  # At least 2 comment lines
    assert blanks >= 0  # Blank lines (may be 0)


def test_count_lines_no_comments() -> None:
    """Test no-comment counting (JSON, Markdown)."""
    # Test JSON
    json_file = Path(__file__).parent / "fixture_small" / "test.json"
    if json_file.exists():
        code, comments, blanks = count_lines_no_comments(json_file)
        assert code >= 3  # At least JSON content
        assert comments == 0  # No comments in JSON
        assert blanks >= 0

    # Test Markdown
    md_file = Path(__file__).parent / "fixture_small" / "test.md"
    if md_file.exists():
        code, comments, blanks = count_lines_no_comments(md_file)
        assert code >= 3  # At least markdown content
        assert comments == 0  # No comments in Markdown
        assert blanks >= 1  # At least 1 blank line


def test_count_lines_by_language() -> None:
    """Test language-specific counting."""
    test_py = Path(__file__).parent / "fixture_small" / "test.py"
    if test_py.exists():
        code, comments, blanks = count_lines(test_py, "Python")
        assert code > 0
        assert comments > 0

    test_js = Path(__file__).parent / "fixture_small" / "test.js"
    if test_js.exists():
        code, comments, blanks = count_lines(test_js, "JavaScript")
        assert code > 0
        assert comments > 0

    test_json = Path(__file__).parent / "fixture_small" / "test.json"
    if test_json.exists():
        code, comments, blanks = count_lines(test_json, "JSON")
        assert code > 0
        assert comments == 0  # JSON has no comments


def test_should_exclude_path() -> None:
    """Test path exclusion logic."""
    root = Path(__file__).parent / "fixture_small"

    # Should exclude binary files
    assert should_exclude_path(Path("test.pdf"), root) is True
    assert should_exclude_path(Path("test.png"), root) is True

    # Should exclude excluded directories
    assert should_exclude_path(Path("__pycache__/test.py"), root) is True
    assert should_exclude_path(Path(".git/test.py"), root) is True

    # Should not exclude normal files
    assert should_exclude_path(Path("test.py"), root) is False
    assert should_exclude_path(Path("test.js"), root) is False


def test_scan_directory() -> None:
    """Test directory scanning."""
    fixture_dir = Path(__file__).parent / "fixture_small"
    if not fixture_dir.exists():
        skip("Fixture directory not found")

    language_stats, files_by_code, files_by_nonempty = scan_directory(
        fixture_dir, use_gitignore=False
    )

    # Should find at least some files
    total_files = sum(stats["files"] for stats in language_stats.values())
    assert total_files > 0

    # Should have Python files
    if "Python" in language_stats:
        assert language_stats["Python"]["files"] > 0
        assert language_stats["Python"]["code"] > 0

    # Should have JSON files
    if "JSON" in language_stats:
        assert language_stats["JSON"]["files"] > 0
        assert language_stats["JSON"]["code"] > 0
        assert language_stats["JSON"]["comments"] == 0  # JSON has no comments

    # Should have Markdown files
    if "Markdown" in language_stats:
        assert language_stats["Markdown"]["files"] > 0
        assert language_stats["Markdown"]["code"] > 0

    # Should have TOP files
    assert len(files_by_code) > 0
    assert len(files_by_nonempty) > 0

    # Files should be sorted by code LOC (descending)
    if len(files_by_code) > 1:
        assert files_by_code[0][0] >= files_by_code[1][0]

    # Files should be sorted by non-empty LOC (descending)
    if len(files_by_nonempty) > 1:
        assert files_by_nonempty[0][0] >= files_by_nonempty[1][0]

    # Code LOC should be <= non-empty LOC for each file
    for code_loc, nonempty_loc, _ in files_by_code:
        assert code_loc <= nonempty_loc


def test_scan_directory_with_gitignore() -> None:
    """Test directory scanning with gitignore."""
    fixture_dir = Path(__file__).parent / "fixture_small"
    if not fixture_dir.exists():
        skip("Fixture directory not found")

    # Scan without gitignore
    stats_no_ignore, _, _ = scan_directory(fixture_dir, use_gitignore=False)

    # Scan with gitignore (if pathspec available)
    try:
        import pathspec

        stats_with_ignore, _, _ = scan_directory(fixture_dir, use_gitignore=True)
        # With gitignore, should have same or fewer files
        total_no = sum(s["files"] for s in stats_no_ignore.values())
        total_with = sum(s["files"] for s in stats_with_ignore.values())
        assert total_with <= total_no
    except ImportError:
        # pathspec not available, skip this test
        pass


# Pytest compatibility
try:
    import pytest

    # Use pytest.skip if available
    def skip(msg: str) -> None:
        """Skip test."""
        pytest.skip(msg)
except ImportError:
    # Fallback if pytest not available
    def skip(msg: str) -> None:
        """Skip test."""
        pass


if __name__ == "__main__":
    # Simple test runner if pytest not available
    import sys

    test_functions = [
        test_get_language,
        test_get_category,
        test_count_lines_python_style,
        test_count_lines_c_style,
        test_count_lines_sql_style,
        test_count_lines_html_xml_style,
        test_count_lines_no_comments,
        test_count_lines_by_language,
        test_should_exclude_path,
        test_scan_directory,
        test_scan_directory_with_gitignore,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"[OK] {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed > 0 else 0)

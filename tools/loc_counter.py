#!/usr/bin/env python3
"""LOC counter fallback implementation when scc/tokei are not available."""

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Excluded directories
EXCLUDED_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "coverage",
    "target",
    "out",
    ".turbo",
    ".idea",
    ".vscode",
    ".pytest_cache",
}

# Excluded file patterns
EXCLUDED_PATTERNS = [
    r"\.min\.",
    r"\.map$",
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"poetry\.lock$",
    r"Pipfile\.lock$",
]

# Binary file extensions (should not be counted as code)
BINARY_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".xlsx",
    ".xls",
    ".doc",
    ".docx",
    ".mxl",
    ".omr",
}

# Language extensions mapping
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "Python": [".py"],
    "JavaScript": [".js"],
    "TypeScript": [".ts", ".tsx"],
    "Go": [".go"],
    "Java": [".java"],
    "C#": [".cs"],
    "C++": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
    "C": [".c", ".h"],
    "Rust": [".rs"],
    "Ruby": [".rb"],
    "PHP": [".php"],
    "Kotlin": [".kt"],
    "Swift": [".swift"],
    "SQL": [".sql"],
    "Shell": [".sh", ".bash"],
    "PowerShell": [".ps1"],
    "YAML": [".yaml", ".yml"],
    "TOML": [".toml"],
    "JSON": [".json"],
    "Markdown": [".md"],
    "XML": [".xml"],
    "HTML": [".html", ".htm"],
    "CSS": [".css"],
    "Other": [],
}

# Language categories
LANGUAGE_CATEGORIES: Dict[str, str] = {
    "JSON": "data",
    "Markdown": "docs",
    "XML": "data",
    "HTML": "code",
    "CSS": "code",
    "YAML": "code",
    "TOML": "code",
}

# Default category
DEFAULT_CATEGORY = "code"

# Build reverse mapping: extension -> language
EXT_TO_LANG: Dict[str, str] = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        EXT_TO_LANG[ext] = lang


def parse_gitignore(root: Path) -> Optional[Set[str]]:
    """Parse .gitignore file and return set of patterns (simplified)."""
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return None

    patterns: Set[str] = set()
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Simple pattern matching (no glob support)
                if line.endswith("/"):
                    patterns.add(line.rstrip("/"))
                else:
                    patterns.add(line)
    except Exception:
        return None

    return patterns


def matches_gitignore(path: Path, root: Path, patterns: Set[str]) -> bool:
    """Check if path matches any gitignore pattern."""
    rel_path = path.relative_to(root)
    path_str = str(rel_path).replace("\\", "/")

    for pattern in patterns:
        # Simple matching (no full glob support)
        if pattern in path_str or path_str.startswith(pattern + "/"):
            return True
        # Wildcard matching (basic)
        if "*" in pattern:
            pattern_re = pattern.replace("*", ".*").replace("/", r"\/")
            if re.search(pattern_re, path_str):
                return True

    return False


def should_exclude_path(
    path: Path, root: Path, gitignore_patterns: Optional[Set[str]] = None
) -> bool:
    """Check if path should be excluded."""
    # Check directory exclusions
    parts = path.parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True

    # Check gitignore
    if gitignore_patterns and matches_gitignore(path, root, gitignore_patterns):
        return True

    # Check binary file extensions
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # Check file pattern exclusions
    path_str = str(path)
    for pattern in EXCLUDED_PATTERNS:
        if re.search(pattern, path_str, re.IGNORECASE):
            return True

    return False


def count_lines_python_style(
    file_path: Path,
) -> Tuple[int, int, int]:
    """Count lines for Python/Shell/YAML style (# comments)."""
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    blank_lines += 1
                elif stripped.startswith("#"):
                    comment_lines += 1
                else:
                    code_lines += 1
    except Exception:
        return (0, 0, 0)

    return (code_lines, comment_lines, blank_lines)


def count_lines_c_style(
    file_path: Path,
) -> Tuple[int, int, int]:
    """Count lines for C/C++/Java/JS/TS/Go/Rust/PHP style (// and /* */ comments)."""
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            in_multiline = False

            for line in f:
                stripped = line.strip()
                original = line.rstrip()

                if not stripped:
                    blank_lines += 1
                    continue

                # Check for multiline comment start/end
                if "/*" in original:
                    in_multiline = True
                if "*/" in original:
                    in_multiline = False

                if in_multiline:
                    comment_lines += 1
                    continue

                # Check for single-line comment
                if "//" in original:
                    # Check if it's inline comment (code before //)
                    before_comment = original.split("//")[0].strip()
                    if before_comment:
                        code_lines += 1
                        comment_lines += 1
                    else:
                        comment_lines += 1
                    continue

                # Check for multiline on same line
                if "/*" in original and "*/" in original:
                    # Comment on same line, check if code before
                    before_comment = original.split("/*")[0].strip()
                    if before_comment:
                        code_lines += 1
                    comment_lines += 1
                    continue

                # Regular code line
                code_lines += 1
    except Exception:
        return (0, 0, 0)

    return (code_lines, comment_lines, blank_lines)


def count_lines_sql_style(
    file_path: Path,
) -> Tuple[int, int, int]:
    """Count lines for SQL style (-- comments)."""
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                original = line.rstrip()

                if not stripped:
                    blank_lines += 1
                    continue

                # Check for SQL comment
                if "--" in original:
                    before_comment = original.split("--")[0].strip()
                    if before_comment:
                        code_lines += 1
                        comment_lines += 1
                    else:
                        comment_lines += 1
                    continue

                code_lines += 1
    except Exception:
        return (0, 0, 0)

    return (code_lines, comment_lines, blank_lines)


def count_lines_html_xml_style(
    file_path: Path,
) -> Tuple[int, int, int]:
    """Count lines for HTML/XML style (<!-- --> comments)."""
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            in_multiline = False

            for line in f:
                stripped = line.strip()
                original = line.rstrip()

                if not stripped:
                    blank_lines += 1
                    continue

                # Check for HTML/XML comment
                if "<!--" in original:
                    in_multiline = True
                if "-->" in original:
                    in_multiline = False

                if in_multiline:
                    comment_lines += 1
                    continue

                # Check for comment on same line
                if "<!--" in original and "-->" in original:
                    before_comment = original.split("<!--")[0].strip()
                    if before_comment:
                        code_lines += 1
                    comment_lines += 1
                    continue

                code_lines += 1
    except Exception:
        return (0, 0, 0)

    return (code_lines, comment_lines, blank_lines)


def count_lines_no_comments(
    file_path: Path,
) -> Tuple[int, int, int]:
    """Count lines for files without comment support (JSON, Markdown)."""
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    blank_lines += 1
                else:
                    code_lines += 1
    except Exception:
        return (0, 0, 0)

    return (code_lines, comment_lines, blank_lines)


def count_lines(file_path: Path, language: str) -> Tuple[int, int, int]:
    """
    Count lines in a file based on language.
    Returns: (code_lines, comment_lines, blank_lines)
    """
    # Python, Shell, PowerShell, YAML
    if language in ("Python", "Shell", "PowerShell", "YAML"):
        return count_lines_python_style(file_path)

    # C, C++, Java, JavaScript, TypeScript, Go, Rust, PHP, C#
    if language in (
        "C",
        "C++",
        "Java",
        "JavaScript",
        "TypeScript",
        "Go",
        "Rust",
        "PHP",
        "C#",
    ):
        return count_lines_c_style(file_path)

    # SQL
    if language == "SQL":
        return count_lines_sql_style(file_path)

    # HTML, XML
    if language in ("HTML", "XML"):
        return count_lines_html_xml_style(file_path)

    # JSON, Markdown, TOML, CSS, Other (no comment detection)
    return count_lines_no_comments(file_path)


def get_language(file_path: Path) -> str:
    """Get language for a file based on extension."""
    ext = file_path.suffix.lower()
    return EXT_TO_LANG.get(ext, "Other")


def get_category(language: str) -> str:
    """Get category for a language."""
    return LANGUAGE_CATEGORIES.get(language, DEFAULT_CATEGORY)


def scan_directory(
    root: Path, use_gitignore: bool = False
) -> Tuple[Dict[str, Dict], List[Tuple[int, int, Path]], List[Tuple[int, int, Path]]]:
    """
    Scan directory and count LOC.
    Returns: (language_stats, top_files_by_code, top_files_by_nonempty)
    """
    language_stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {
            "code": 0,
            "comments": 0,
            "blanks": 0,
            "files": 0,
            "non_empty": 0,
        }
    )

    files_by_code: List[Tuple[int, int, Path]] = []  # (code_loc, nonempty_loc, path)
    files_by_nonempty: List[Tuple[int, int, Path]] = []  # (nonempty_loc, code_loc, path)

    # Parse gitignore if requested
    gitignore_spec = None
    gitignore_patterns: Optional[Set[str]] = None
    if use_gitignore:
        gitignore_path = root / ".gitignore"
        if gitignore_path.exists():
            try:
                import pathspec

                with open(gitignore_path, "r", encoding="utf-8") as f:
                    gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
            except ImportError:
                # Fallback to simple parsing
                gitignore_patterns = parse_gitignore(root)
            except Exception:
                gitignore_patterns = None

    # Use os.walk for better performance
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Check basic exclusions
            if should_exclude_path(file_path, root, None):
                continue

            # Check gitignore (pathspec if available, otherwise simple patterns)
            if use_gitignore:
                if gitignore_spec is not None:
                    # Use pathspec
                    try:
                        rel_path = file_path.relative_to(root)
                        if gitignore_spec.match_file(str(rel_path).replace("\\", "/")):
                            continue
                    except Exception:
                        pass
                elif gitignore_patterns is not None:
                    # Use simple pattern matching
                    if matches_gitignore(file_path, root, gitignore_patterns):
                        continue

            lang = get_language(file_path)
            code, comments, blanks = count_lines(file_path, lang)

            if code + comments + blanks > 0:  # Only count non-empty files
                non_empty = code + comments
                category = get_category(lang)

                language_stats[lang]["code"] += code
                language_stats[lang]["comments"] += comments
                language_stats[lang]["blanks"] += blanks
                language_stats[lang]["files"] += 1
                language_stats[lang]["non_empty"] += non_empty

                files_by_code.append((code, non_empty, file_path))
                files_by_nonempty.append((non_empty, code, file_path))

    # Sort files
    files_by_code.sort(reverse=True, key=lambda x: x[0])
    files_by_nonempty.sort(reverse=True, key=lambda x: x[0])

    return (dict(language_stats), files_by_code, files_by_nonempty)


def get_git_commit_hash(root: Path) -> str:
    """Get git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def generate_report(
    root: Path,
    language_stats: Dict[str, Dict[str, int]],
    files_by_code: List[Tuple[int, int, Path]],
    files_by_nonempty: List[Tuple[int, int, Path]],
    use_gitignore: bool,
    command: str,
    out_path: Optional[Path] = None,
) -> Path:
    """Generate LOC report markdown file."""
    if out_path is None:
        report_dir = root / "reports"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / "loc_report.md"
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_path = out_path

    # Calculate totals
    total_code = sum(stats["code"] for stats in language_stats.values())
    total_comments = sum(stats["comments"] for stats in language_stats.values())
    total_blanks = sum(stats["blanks"] for stats in language_stats.values())
    total_non_empty = sum(stats["non_empty"] for stats in language_stats.values())
    total_files = sum(stats["files"] for stats in language_stats.values())

    git_hash = get_git_commit_hash(root)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Repo LOC Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Commit:** `{git_hash}`\n\n")

        f.write("## Summary\n\n")
        f.write("| Metric | Count |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Total Files | {total_files:,} |\n")
        f.write(f"| **Total Code LOC** | **{total_code:,}** |\n")
        f.write(f"| **Total Non-empty LOC** | **{total_non_empty:,}** |\n")
        f.write(f"| Total Comments | {total_comments:,} |\n")
        f.write(f"| Total Blanks | {total_blanks:,} |\n")
        f.write(
            f"| **Total Lines** | **{total_code + total_comments + total_blanks:,}** |\n\n"
        )

        f.write("## By Language (Code LOC)\n\n")
        f.write(
            "| Language | Category | Files | Code LOC | Comment LOC | Blank LOC | Non-empty LOC |\n"
        )
        f.write(
            "|----------|----------|-------|----------|-------------|-----------|---------------|\n"
        )
        sorted_langs = sorted(
            language_stats.items(), key=lambda x: x[1]["code"], reverse=True
        )
        for lang, stats in sorted_langs:
            if stats["code"] > 0:
                category = get_category(lang)
                f.write(
                    f"| {lang} | {category} | {stats['files']:,} | {stats['code']:,} | "
                    f"{stats['comments']:,} | {stats['blanks']:,} | {stats['non_empty']:,} |\n"
                )

        f.write("\n## By Language (Non-empty LOC)\n\n")
        f.write(
            "| Language | Category | Files | Code LOC | Comment LOC | Blank LOC | Non-empty LOC |\n"
        )
        f.write(
            "|----------|----------|-------|----------|-------------|-----------|---------------|\n"
        )
        sorted_langs_nonempty = sorted(
            language_stats.items(), key=lambda x: x[1]["non_empty"], reverse=True
        )
        for lang, stats in sorted_langs_nonempty:
            if stats["code"] > 0:
                category = get_category(lang)
                f.write(
                    f"| {lang} | {category} | {stats['files']:,} | {stats['code']:,} | "
                    f"{stats['comments']:,} | {stats['blanks']:,} | {stats['non_empty']:,} |\n"
                )

        f.write("\n## Exclusions\n\n")
        f.write("The following directories and patterns were excluded:\n\n")
        f.write("**Directories:**\n")
        for dir_name in sorted(EXCLUDED_DIRS):
            f.write(f"- `{dir_name}/`\n")
        f.write("\n**File Patterns:**\n")
        for pattern in EXCLUDED_PATTERNS:
            f.write(f"- `{pattern}`\n")
        f.write("\n**Binary Extensions:**\n")
        for ext in sorted(BINARY_EXTENSIONS):
            f.write(f"- `{ext}`\n")
        if use_gitignore:
            f.write("\n**Gitignore:** Used (if available)\n")

        f.write("\n## TOP-20 Files by Code LOC\n\n")
        f.write("| Rank | Code LOC | Non-empty LOC | Path |\n")
        f.write("|------|----------|---------------|------|\n")
        for i, (code_loc, nonempty_loc, path) in enumerate(files_by_code[:20], 1):
            rel_path = path.relative_to(root)
            f.write(f"| {i} | {code_loc:,} | {nonempty_loc:,} | `{rel_path}` |\n")

        f.write("\n## TOP-20 Files by Non-empty LOC\n\n")
        f.write("| Rank | Non-empty LOC | Code LOC | Path |\n")
        f.write("|------|---------------|----------|------|\n")
        for i, (nonempty_loc, code_loc, path) in enumerate(files_by_nonempty[:20], 1):
            rel_path = path.relative_to(root)
            f.write(f"| {i} | {nonempty_loc:,} | {code_loc:,} | `{rel_path}` |\n")

        f.write("\n## Method\n\n")
        f.write("**Tool:** Fallback (Python script)\n\n")
        f.write("**Command:**\n")
        f.write("```bash\n")
        f.write(f"{command}\n")
        f.write("```\n\n")
        f.write(
            "**Note:** scc and tokei were not available, so a custom Python script was used.\n"
        )
        f.write(
            "\n**Binary files excluded:** PDF, PNG, JPG, and other binary formats are not counted.\n"
        )

    print(f"[OK] Report saved to: {report_path}")
    return report_path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LOC counter fallback implementation"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory to scan (default: current working directory)",
    )
    parser.add_argument(
        "--use-gitignore",
        action="store_true",
        help="Use .gitignore file for exclusions (requires pathspec package)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output report path (default: <root>/reports/loc_report.md)",
    )

    args = parser.parse_args()

    # Determine root (resolve relative to current working directory)
    root = args.root.resolve()

    if not root.exists():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    if not root.is_dir():
        print(f"Error: Root path is not a directory: {root}", file=sys.stderr)
        return 1

    print(f"Scanning {root}...")
    if args.use_gitignore:
        print("Using .gitignore (if available)")

    language_stats, files_by_code, files_by_nonempty = scan_directory(
        root, use_gitignore=args.use_gitignore
    )

    # Calculate totals
    total_code = sum(stats["code"] for stats in language_stats.values())
    total_comments = sum(stats["comments"] for stats in language_stats.values())
    total_blanks = sum(stats["blanks"] for stats in language_stats.values())
    total_non_empty = sum(stats["non_empty"] for stats in language_stats.values())
    total_files = sum(stats["files"] for stats in language_stats.values())

    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total Files: {total_files:,}")
    print(f"Total Code LOC: {total_code:,}")
    print(f"Total Non-empty LOC: {total_non_empty:,}")
    print(f"Total Comments: {total_comments:,}")
    print(f"Total Blanks: {total_blanks:,}")
    print(f"Total Lines: {total_code + total_comments + total_blanks:,}")

    # Print by language (Code LOC)
    print(f"\n=== BY LANGUAGE (Code LOC) ===")
    sorted_langs = sorted(
        language_stats.items(), key=lambda x: x[1]["code"], reverse=True
    )
    for lang, stats in sorted_langs:
        if stats["code"] > 0:
            category = get_category(lang)
            print(
                f"{lang:20} [{category:4}] | Files: {stats['files']:4} | "
                f"Code: {stats['code']:7,} | Comments: {stats['comments']:6,} | "
                f"Blanks: {stats['blanks']:6,} | Non-empty: {stats['non_empty']:7,}"
            )

    # Print TOP-20 files by Code LOC
    print(f"\n=== TOP-20 FILES BY CODE LOC ===")
    for i, (code_loc, nonempty_loc, path) in enumerate(files_by_code[:20], 1):
        rel_path = path.relative_to(root)
        print(f"{i:2}. Code: {code_loc:6,} | Non-empty: {nonempty_loc:6,} | {rel_path}")

    # Print TOP-20 files by Non-empty LOC
    print(f"\n=== TOP-20 FILES BY NON-EMPTY LOC ===")
    for i, (nonempty_loc, code_loc, path) in enumerate(files_by_nonempty[:20], 1):
        rel_path = path.relative_to(root)
        print(
            f"{i:2}. Non-empty: {nonempty_loc:6,} | Code: {code_loc:6,} | {rel_path}"
        )

    # Build command string (repo-agnostic)
    script_invocation = Path(sys.argv[0]).as_posix()
    cmd_parts = ["python", script_invocation]
    if args.root != Path("."):
        cmd_parts += ["--root", str(args.root)]
    if args.use_gitignore:
        cmd_parts.append("--use-gitignore")
    if args.out:
        cmd_parts += ["--out", str(args.out)]
    command = " ".join(cmd_parts)

    # Generate report
    generate_report(
        root,
        language_stats,
        files_by_code,
        files_by_nonempty,
        args.use_gitignore,
        command,
        args.out,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

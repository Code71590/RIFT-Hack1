"""
Deterministic bug fixer — fixes SYNTAX, IMPORT, LINTING, and INDENTATION
errors WITHOUT any LLM calls. Uses Python's ast module, flake8, and importlib.

This module is called BEFORE the LLM, so only genuinely hard bugs
(LOGIC, TYPE_ERROR) are sent to the LLM — saving cost and time.
"""

import os
import re
import ast
import subprocess
import importlib.util


# ═══════════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════════

def _log(tag, msg):
    print(f"[DETERMINISTIC] [{tag}] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  1. SYNTAX ERROR DETECTION & FIX (ast.parse)
# ═══════════════════════════════════════════════════════════════════

def _detect_syntax_errors(repo_path: str) -> list:
    """
    Try to ast.parse() every .py file. If it fails, extract the
    SyntaxError location and try to auto-fix common patterns.
    """
    fixes = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".tox"}]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, repo_path).replace("\\", "/")

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                line_no = e.lineno or 0
                msg = str(e.msg) if e.msg else ""
                _log("SYNTAX", f"SyntaxError in {rel_path}:{line_no} — {msg}")

                fix = _try_fix_syntax(fpath, rel_path, source, line_no, msg)
                if fix:
                    fixes.append(fix)

    return fixes


def _try_fix_syntax(fpath, rel_path, source, line_no, error_msg):
    """Try to auto-fix common syntax errors."""
    lines = source.split("\n")
    if line_no < 1 or line_no > len(lines):
        return None

    line = lines[line_no - 1]

    # Pattern 1: Missing colon after def/class/if/elif/else/for/while/with/try/except/finally
    # e.g. "def validate_email(email)" → "def validate_email(email):"
    colon_keywords = r"^\s*(def\s+\w+\(.*\)|class\s+\w+.*|if\s+.+|elif\s+.+|else|for\s+.+|while\s+.+|with\s+.+|try|except.*|finally)\s*$"
    if re.match(colon_keywords, line) and not line.rstrip().endswith(":"):
        old_code = line.rstrip()
        new_code = old_code + ":"
        _log("SYNTAX", f"  Fix: adding missing colon → {new_code}")
        return {
            "file": rel_path,
            "line": line_no,
            "old_code": old_code,
            "new_code": new_code,
            "bug_type": "SYNTAX",
            "description": f"Add missing colon at end of statement",
        }

    # Pattern 2: Missing closing parenthesis/bracket
    if "expected ':'" in error_msg.lower() or "expected ':'":
        # Check the line before for missing colon
        if line_no >= 2:
            prev_line = lines[line_no - 2]
            if re.match(colon_keywords, prev_line) and not prev_line.rstrip().endswith(":"):
                old_code = prev_line.rstrip()
                new_code = old_code + ":"
                _log("SYNTAX", f"  Fix: adding missing colon on prev line → {new_code}")
                return {
                    "file": rel_path,
                    "line": line_no - 1,
                    "old_code": old_code,
                    "new_code": new_code,
                    "bug_type": "SYNTAX",
                    "description": f"Add missing colon at end of function/class definition",
                }

    return None


# ═══════════════════════════════════════════════════════════════════
#  2. IMPORT ERROR DETECTION & FIX (importlib)
# ═══════════════════════════════════════════════════════════════════

def _detect_import_errors(repo_path: str) -> list:
    """
    Scan all .py files for import statements.
    Check if the imported module actually exists (using importlib).
    If not, generate a fix to remove the import line.
    """
    fixes = []

    # Build a set of all local module names (files and directories in repo root + src/)
    local_modules = set()
    for entry in os.listdir(repo_path):
        entry_path = os.path.join(repo_path, entry)
        if os.path.isdir(entry_path) and entry not in {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".tox"}:
            local_modules.add(entry)
        elif entry.endswith(".py"):
            local_modules.add(entry[:-3])  # Remove .py extension

    # Also check src/ subdirectory for modules
    src_dir = os.path.join(repo_path, "src")
    if os.path.isdir(src_dir):
        for entry in os.listdir(src_dir):
            if entry.endswith(".py") and entry != "__init__.py":
                local_modules.add(entry[:-3])
            elif os.path.isdir(os.path.join(src_dir, entry)) and entry != "__pycache__":
                local_modules.add(entry)

    _log("IMPORT", f"Local modules detected: {sorted(local_modules)}")

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".tox"}]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            # Skip test files — they import project modules which are always valid
            if fname.startswith("test_") or fname.endswith("_test.py") or fname == "conftest.py":
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, repo_path).replace("\\", "/")

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue

            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                # Match "import xyz" or "from xyz import ..."
                m_import = re.match(r"^import\s+([\w\.]+)", stripped)
                m_from = re.match(r"^from\s+([\w\.]+)\s+import", stripped)

                module_name = None
                if m_import:
                    module_name = m_import.group(1)
                elif m_from:
                    module_name = m_from.group(1)

                if not module_name:
                    continue

                # Skip relative imports
                if module_name.startswith("."):
                    continue

                # Skip project-internal imports
                top_module = module_name.split(".")[0]
                if top_module in local_modules:
                    continue

                # Try to find the module in the Python environment
                try:
                    spec = importlib.util.find_spec(top_module)
                    if spec is not None:
                        continue  # Module exists, skip
                except (ModuleNotFoundError, ValueError):
                    pass

                # Module doesn't exist — generate removal fix
                _log("IMPORT", f"Non-existent module '{module_name}' in {rel_path}:{i+1}")
                fixes.append({
                    "file": rel_path,
                    "line": i + 1,
                    "old_code": line.rstrip("\n").rstrip("\r"),
                    "new_code": "",
                    "bug_type": "IMPORT",
                    "description": f"Remove import of non-existent module '{module_name}'",
                })

    return fixes


# ═══════════════════════════════════════════════════════════════════
#  3. LINTING ERROR DETECTION & FIX (flake8 F401 — unused imports)
# ═══════════════════════════════════════════════════════════════════

def _detect_linting_errors(repo_path: str) -> list:
    """
    Run flake8 with --select=F401 to find unused imports in source files only.
    Skip test files (they have legitimate pytest imports etc.).
    """
    fixes = []

    # Only run flake8 on src/ directory (not tests/) to avoid false positives
    # If no src/ dir, run on root but exclude tests/
    src_dir = os.path.join(repo_path, "src")
    if os.path.isdir(src_dir):
        flake8_target = "src"
    else:
        flake8_target = "."

    try:
        cmd = ["flake8", "--select=F401",
               "--exclude=tests,test_*,*_test.py,conftest.py",
               "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
               flake8_target]
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        if not output:
            return fixes

        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(":", 4)
            if len(parts) < 5:
                continue

            fpath = parts[0].replace("\\", "/")
            # Normalize path: strip leading "./"
            if fpath.startswith("./"):
                fpath = fpath[2:]

            line_no = int(parts[1])
            code = parts[3].strip()
            text = parts[4].strip()

            if code != "F401":
                continue

            # Extract module name from flake8 message
            module_match = re.search(r"'([\w\.]+)'", text)
            module_name = module_match.group(1) if module_match else "unknown"

            # Skip pytest — test files legitimately import it
            if module_name == "pytest":
                continue

            # Read the actual line
            abs_path = os.path.join(repo_path, fpath)
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    file_lines = f.readlines()
                if line_no <= len(file_lines):
                    old_code = file_lines[line_no - 1].rstrip("\n").rstrip("\r")

                    _log("LINTING", f"Unused import '{module_name}' in {fpath}:{line_no}")
                    fixes.append({
                        "file": fpath,
                        "line": line_no,
                        "old_code": old_code,
                        "new_code": "",
                        "bug_type": "LINTING",
                        "description": f"Remove unused import '{module_name}'",
                    })
            except Exception:
                continue

    except FileNotFoundError:
        _log("WARN", "flake8 not installed — skipping linting checks")
    except subprocess.TimeoutExpired:
        _log("WARN", "flake8 timed out")
    except Exception as e:
        _log("WARN", f"flake8 error: {e}")

    return fixes


# ═══════════════════════════════════════════════════════════════════
#  4. INDENTATION ERROR DETECTION & FIX (flake8 E111, E117)
# ═══════════════════════════════════════════════════════════════════

def _detect_indentation_errors(repo_path: str) -> list:
    """
    Run flake8 with --select=E111,E117 to find indentation errors.
    Auto-fix to PEP8 standard (4-space indentation).
    """
    fixes = []
    try:
        # Only check src/ for indentation, exclude tests
        src_dir = os.path.join(repo_path, "src")
        flake8_target = "src" if os.path.isdir(src_dir) else "."

        result = subprocess.run(
            ["flake8", "--select=E111,E117,E112,E113,E114,E115,E116",
             "--exclude=tests,test_*,*_test.py,conftest.py",
             "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s", flake8_target],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        if not output:
            return fixes

        # Group errors by file to fix them together
        file_errors = {}
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(":", 4)
            if len(parts) < 5:
                continue

            fpath = parts[0].replace("\\", "/")
            # Normalize path: strip leading "./"
            if fpath.startswith("./"):
                fpath = fpath[2:]
            line_no = int(parts[1])
            code = parts[3].strip()
            text = parts[4].strip()

            if fpath not in file_errors:
                file_errors[fpath] = []
            file_errors[fpath].append((line_no, code, text))

        for fpath, errors in file_errors.items():
            abs_path = os.path.join(repo_path, fpath)
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    file_lines = f.readlines()
            except Exception:
                continue

            for line_no, code, text in errors:
                if line_no > len(file_lines):
                    continue

                old_line = file_lines[line_no - 1]
                old_code = old_line.rstrip("\n").rstrip("\r")
                content = old_line.lstrip()

                # Determine the correct indentation level
                # We need to figure out the nesting depth from context
                correct_indent = _determine_correct_indent(file_lines, line_no - 1)
                new_code = correct_indent + content.rstrip("\n").rstrip("\r")

                if old_code != new_code:
                    _log("INDENTATION", f"Fixing indent in {fpath}:{line_no} ({code})")
                    fixes.append({
                        "file": fpath,
                        "line": line_no,
                        "old_code": old_code,
                        "new_code": new_code,
                        "bug_type": "INDENTATION",
                        "description": f"Fix indentation to PEP8 standard (4-space)",
                    })

    except FileNotFoundError:
        _log("WARN", "flake8 not installed — skipping indentation checks")
    except subprocess.TimeoutExpired:
        _log("WARN", "flake8 timed out")
    except Exception as e:
        _log("WARN", f"flake8 error: {e}")

    return fixes


def _determine_correct_indent(lines, idx):
    """
    Determine the correct indentation for a line based on context.
    
    Strategy: search backward for the nearest block opener (line ending with ':')
    and use its indent + 4 spaces. This handles chained mis-indented lines
    correctly, because it doesn't trust the immediate previous line's indent.
    """
    # Search backward for the nearest block-opening line (ends with ':')
    for i in range(idx - 1, -1, -1):
        prev = lines[i]
        stripped = prev.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # If we find a line ending with ':', the current line should be indented
        # one level deeper than that line
        if stripped.endswith(":"):
            opener_indent = len(prev) - len(prev.lstrip())
            return " " * (opener_indent + 4)

        # If we find a 'return', 'break', 'continue', 'pass', 'raise' — these
        # end a block, so the current line is at the same level as the block opener
        for kw in ("return ", "return\n", "break", "continue", "pass", "raise "):
            if stripped.startswith(kw) or stripped == kw.strip():
                # Go further back to find the block opener
                continue

        # If this previous line has correct-looking indent (multiple of 4), use it
        prev_indent = len(prev) - len(prev.lstrip())
        if prev_indent % 4 == 0:
            return " " * prev_indent

        # Previous line also has bad indent — keep searching backward
        continue

    return ""  # Top level


# ═══════════════════════════════════════════════════════════════════
#  5. DEDUPLICATE FIXES
# ═══════════════════════════════════════════════════════════════════

def _normalize_path(p: str) -> str:
    """Normalize a path: strip leading './' and backslashes."""
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p


def _deduplicate_fixes(fixes: list) -> list:
    """Remove duplicate fixes (same file + same line), normalizing paths."""
    seen = set()
    unique = []
    for fix in fixes:
        # Normalize the path for comparison and storage
        fix["file"] = _normalize_path(fix["file"])
        key = (fix["file"], fix["line"])
        if key not in seen:
            seen.add(key)
            unique.append(fix)
    return unique


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def detect_and_fix_deterministic(repo_path: str) -> dict:
    """
    Run all deterministic bug detectors on the repo.
    Returns fixes in the same format as llm.ask_for_fixes().

    This should be called BEFORE the LLM — any bugs fixed here
    don't need to be sent to the LLM at all.
    """
    _log("START", f"Running deterministic bug detection on {repo_path}")

    all_fixes = []

    # 1. Syntax errors (must be fixed first — they block everything else)
    _log("PHASE", "Phase 1: Checking for syntax errors (ast.parse)...")
    syntax_fixes = _detect_syntax_errors(repo_path)
    all_fixes.extend(syntax_fixes)
    _log("PHASE", f"  Found {len(syntax_fixes)} syntax errors")

    # 2. Import errors (non-existent modules)
    _log("PHASE", "Phase 2: Checking for import errors (importlib)...")
    import_fixes = _detect_import_errors(repo_path)
    all_fixes.extend(import_fixes)
    _log("PHASE", f"  Found {len(import_fixes)} import errors")

    # 3. Linting errors (unused imports) — only if no syntax errors block flake8
    _log("PHASE", "Phase 3: Checking for linting errors (flake8 F401)...")
    linting_fixes = _detect_linting_errors(repo_path)
    all_fixes.extend(linting_fixes)
    _log("PHASE", f"  Found {len(linting_fixes)} linting errors")

    # 4. Indentation errors
    _log("PHASE", "Phase 4: Checking for indentation errors (flake8 E111/E117)...")
    indent_fixes = _detect_indentation_errors(repo_path)
    all_fixes.extend(indent_fixes)
    _log("PHASE", f"  Found {len(indent_fixes)} indentation errors")

    # Deduplicate
    all_fixes = _deduplicate_fixes(all_fixes)

    _log("DONE", f"Total deterministic fixes: {len(all_fixes)}")
    for i, fix in enumerate(all_fixes, 1):
        _log("FIX", f"  #{i}: [{fix['bug_type']}] {fix['file']}:{fix['line']} — {fix['description']}")

    commit_title = "[AI-AGENT] Fix syntax, import, linting, and indentation errors (deterministic)"

    return {
        "fixes": all_fixes,
        "commit_title": commit_title,
    }

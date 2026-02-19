"""
Apply code fixes to files in the repository.
"""

import os


def apply_fixes(repo_path: str, fixes: list) -> list:
    """
    Apply line-level code fixes to files.
    
    Args:
        repo_path: Path to the cloned repository.
        fixes: List of fix dicts from llm.ask_for_fixes().
    
    Returns:
        List of fix dicts with added 'status' field ('applied' or 'failed').
    """
    results = []

    for fix in fixes:
        file_path = os.path.join(repo_path, fix["file"])
        try:
            if not os.path.exists(file_path):
                fix["status"] = "failed"
                fix["status_message"] = f"File not found: {fix['file']}"
                results.append(fix)
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            line_idx = fix["line"] - 1  # Convert to 0-indexed

            if line_idx < 0 or line_idx >= len(lines):
                fix["status"] = "failed"
                fix["status_message"] = f"Line {fix['line']} out of range (file has {len(lines)} lines)"
                results.append(fix)
                continue

            old_code = fix.get("old_code", "").strip()
            new_code = fix.get("new_code", "")

            # Verify the line matches what we expect
            actual_line = lines[line_idx].rstrip("\n").rstrip("\r")
            if old_code and old_code.strip() != actual_line.strip():
                # Try to find the line elsewhere in the file
                found = False
                for i, line in enumerate(lines):
                    if line.rstrip("\n").rstrip("\r").strip() == old_code.strip():
                        line_idx = i
                        found = True
                        break
                if not found:
                    fix["status"] = "failed"
                    fix["status_message"] = f"Expected '{old_code}' at line {fix['line']}, found '{actual_line}'"
                    results.append(fix)
                    continue

            # Apply the fix
            if new_code == "" or new_code is None:
                # Delete the line (remove unused import, etc.)
                lines.pop(line_idx)
                print(f"[FIXER] Removed line {fix['line']} from {fix['file']}")
            else:
                # Preserve original indentation/newline
                original_newline = "\n"
                if lines[line_idx].endswith("\r\n"):
                    original_newline = "\r\n"

                lines[line_idx] = new_code + original_newline
                print(f"[FIXER] Replaced line {fix['line']} in {fix['file']}")

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            fix["status"] = "applied"
            fix["status_message"] = "Fix applied successfully"
            results.append(fix)

        except Exception as e:
            fix["status"] = "failed"
            fix["status_message"] = str(e)
            results.append(fix)

    applied_count = sum(1 for r in results if r["status"] == "applied")
    print(f"[FIXER] Applied {applied_count}/{len(fixes)} fixes")

    return results

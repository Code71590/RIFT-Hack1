"""
Run tests in the cloned repository and parse the results.
"""

import os
import re
import subprocess


def run_tests(repo_path: str, test_command: str, skip_deps: bool = False) -> dict:
    """
    Run the test suite and parse results.
    
    Args:
        repo_path: Path to the cloned repository.
        test_command: Command to run tests (e.g., 'pytest -v').
        skip_deps: If True, skip installing dependencies (already done).
    
    Returns:
        dict with keys: passed, failed, errors, raw_output
    """
    print(f"[TEST_RUNNER] Running: {test_command} in {repo_path}")

    # Install dependencies first if requirements.txt exists (skip if already done)
    if not skip_deps:
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            print("[TEST_RUNNER] Installing dependencies...")
            subprocess.run(
                ["pip", "install", "-r", req_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
    else:
        print("[TEST_RUNNER] Skipping dependency install (cached)")

    # Run the tests
    cmd_parts = test_command.split()
    result = subprocess.run(
        cmd_parts,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
    )

    raw_output = result.stdout + "\n" + result.stderr
    print(f"[TEST_RUNNER] Return code: {result.returncode}")

    # Parse pytest output
    errors = parse_pytest_output(raw_output, repo_path)
    passed = len(re.findall(r"PASSED", raw_output))
    failed = len(re.findall(r"FAILED", raw_output))

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "raw_output": raw_output,
    }


def parse_pytest_output(output: str, repo_path: str) -> list:
    """
    Parse pytest verbose output to extract failure details.
    
    Returns:
        List of dicts: {test_name, file, line, error_message}
    """
    errors = []

    # Match FAILED lines like: FAILED tests/test_calculator.py::test_add - AssertionError: ...
    failed_pattern = re.compile(r"FAILED\s+([\w/\\\.]+)::(\w+)")
    failed_matches = failed_pattern.findall(output)

    # Also look for error sections in the output
    # Pytest shows errors between ===== FAILURES ===== and ===== short test summary =====
    failure_sections = re.split(r"_{3,}\s+([\w\.]+)\s+_{3,}", output)

    # Parse individual error blocks
    error_block_pattern = re.compile(
        r"_{5,}\s+(\S+)\s+_{5,}(.*?)(?=_{5,}|\Z)",
        re.DOTALL,
    )
    error_blocks = error_block_pattern.findall(output)

    for test_name, block in error_blocks:
        # Try to extract file and line from the block
        file_line_match = re.search(r"([\w/\\]+\.py):(\d+)", block)
        file_path = file_line_match.group(1) if file_line_match else "unknown"
        line_num = int(file_line_match.group(2)) if file_line_match else 0

        # Get the error message (last few lines usually contain the assertion)
        lines = block.strip().split("\n")
        error_msg = ""
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("_"):
                error_msg = line
                break

        errors.append({
            "test_name": test_name.strip(),
            "file": file_path.replace("\\", "/"),
            "line": line_num,
            "error_message": error_msg,
        })

    # If no blocks found, try to extract from FAILED lines
    if not errors and failed_matches:
        for file_path, test_name in failed_matches:
            errors.append({
                "test_name": test_name,
                "file": file_path.replace("\\", "/"),
                "line": 0,
                "error_message": f"Test {test_name} failed",
            })

    # Also catch collection errors (syntax errors, import errors)
    collection_errors = re.findall(
        r"ERROR\s+collecting\s+([\w/\\\.]+)\s*.*?\n(.*?)(?=\n\S|\Z)",
        output,
        re.DOTALL,
    )
    for file_path, error_detail in collection_errors:
        # Try to find line number in error detail
        line_match = re.search(r"line\s+(\d+)", error_detail)
        line_num = int(line_match.group(1)) if line_match else 0

        errors.append({
            "test_name": f"collection_error:{file_path}",
            "file": file_path.replace("\\", "/"),
            "line": line_num,
            "error_message": error_detail.strip()[:200],
        })

    return errors

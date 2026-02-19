"""
Analyze a cloned repository: build file tree, discover test files, detect language.
"""

import os

# Directories to skip when walking the repo
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env", ".tox", ".pytest_cache"}


def build_file_tree(repo_path: str, prefix: str = "") -> str:
    """
    Build a text representation of the file tree.
    
    Returns:
        A string like:
            src/
            ├── calculator.py
            ├── utils.py
            └── validator.py
    """
    lines = []
    entries = sorted(os.listdir(repo_path))
    # Filter out skip dirs
    entries = [e for e in entries if e not in SKIP_DIRS]

    for i, entry in enumerate(entries):
        path = os.path.join(repo_path, entry)
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry}")

        if os.path.isdir(path):
            extension = "    " if i == len(entries) - 1 else "│   "
            subtree = build_file_tree(path, prefix + extension)
            if subtree:
                lines.append(subtree)

    return "\n".join(lines)


def discover_test_files(repo_path: str) -> list:
    """
    Find all test files in the repository.
    Looks for files matching test_*.py or *_test.py patterns.
    
    Returns:
        List of relative paths to test files.
    """
    test_files = []
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden/unwanted dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if (f.startswith("test_") or f.endswith("_test.py")) and f.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, f), repo_path)
                test_files.append(rel_path)
    return sorted(test_files)


def detect_language(repo_path: str) -> str:
    """
    Simple language detection based on file extensions.
    """
    ext_counts = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rb": "ruby",
    }

    if not ext_counts:
        return "unknown"

    top_ext = max(ext_counts, key=ext_counts.get)
    return lang_map.get(top_ext, "unknown")


def infer_test_command(language: str, repo_path: str) -> str:
    """
    Infer the test command based on the language and repo structure.
    """
    if language == "python":
        # Check if pytest is in requirements
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r") as f:
                content = f.read()
                if "pytest" in content:
                    return "pytest -v"
        return "pytest -v"
    elif language == "javascript":
        return "npm test"
    elif language == "typescript":
        return "npm test"
    elif language == "java":
        return "mvn test"
    else:
        return "pytest -v"


def analyze_repo(repo_path: str) -> dict:
    """
    Full analysis of a repository.
    
    Returns:
        dict with keys: tree, test_files, language, test_command
    """
    tree = build_file_tree(repo_path)
    test_files = discover_test_files(repo_path)
    language = detect_language(repo_path)
    test_command = infer_test_command(language, repo_path)

    print(f"[ANALYZER] Language: {language}")
    print(f"[ANALYZER] Test files found: {len(test_files)}")
    print(f"[ANALYZER] Test command: {test_command}")

    return {
        "tree": tree,
        "test_files": test_files,
        "language": language,
        "test_command": test_command,
    }

"""
Clone a GitHub repository into a local workspace directory.
"""

import os
import shutil
import subprocess
import time
import stat


def _force_remove_readonly(func, path, exc_info):
    """Handle read-only files on Windows during rmtree."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _remove_dir(path):
    """Remove a directory, handling Windows lock issues."""
    try:
        shutil.rmtree(path, onerror=_force_remove_readonly)
    except Exception:
        # Fallback: use cmd /c rmdir on Windows
        try:
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", path],
                capture_output=True, text=True, timeout=30,
            )
            time.sleep(1)
        except Exception:
            pass
    # If still exists, wait and retry once
    if os.path.exists(path):
        time.sleep(2)
        try:
            shutil.rmtree(path, onerror=_force_remove_readonly)
        except Exception as e:
            print(f"[CLONE] Warning: Could not fully remove {path}: {e}")


def clone_repo(github_url: str, workspace_dir: str) -> str:
    """
    Clone a GitHub repository into workspace_dir.
    
    Args:
        github_url: The HTTPS URL of the GitHub repository.
        workspace_dir: Base directory where repos are cloned.
    
    Returns:
        The absolute path to the cloned repository.
    """
    # Extract repo name from URL
    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(workspace_dir, repo_name)

    # If already exists, remove it for a fresh clone
    if os.path.exists(repo_path):
        _remove_dir(repo_path)

    os.makedirs(workspace_dir, exist_ok=True)

    print(f"[CLONE] Cloning {github_url} into {repo_path}...")
    result = subprocess.run(
        ["git", "clone", github_url, repo_path],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {result.stderr}")

    print(f"[CLONE] Successfully cloned to {repo_path}")
    return repo_path

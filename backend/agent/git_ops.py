"""
Git operations: create branches, commit with [AI-AGENT] prefix, push.
"""

import subprocess
import os


def make_branch_name(team_name: str, leader_name: str) -> str:
    """
    Create branch name in format: TEAM_NAME_LEADER_NAME_AI_Fix
    All uppercase, spaces replaced with underscores, no special characters.
    """
    def clean(s):
        # Remove special characters, replace spaces with underscores, uppercase
        cleaned = "".join(c if c.isalnum() or c == " " else "" for c in s)
        return cleaned.strip().replace(" ", "_").upper()

    team = clean(team_name)
    leader = clean(leader_name)
    return f"{team}_{leader}_AI_Fix"


def create_branch(repo_path: str, branch_name: str):
    """
    Create and checkout a new branch.
    """
    print(f"[GIT] Creating branch: {branch_name}")

    # Check if branch already exists
    result = subprocess.run(
        ["git", "branch", "--list", branch_name],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if branch_name in result.stdout:
        # Branch exists, just checkout
        subprocess.run(
            ["git", "checkout", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
    else:
        # Create new branch
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create branch: {result.stderr}")

    print(f"[GIT] On branch: {branch_name}")


def commit_and_push(repo_path: str, commit_message: str, branch_name: str) -> dict:
    """
    Stage all changes, commit, and push to remote.
    
    Handles authentication via:
      1. GITHUB_TOKEN env var (embeds token in remote URL)
      2. GitHub CLI (gh auth setup-git)
      3. Falls back to default git credential helper
    """
    print(f"[GIT] Committing: {commit_message}")

    # Stage all changes
    subprocess.run(
        ["git", "add", "-A"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Might be nothing to commit
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print("[GIT] Nothing to commit")
            return {
                "success": True,
                "commit_hash": "",
                "branch": branch_name,
                "message": "Nothing to commit",
                "push_success": True,
            }
        raise RuntimeError(f"Failed to commit: {result.stderr}")

    # Get commit hash
    hash_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    commit_hash = hash_result.stdout.strip()

    # ── Setup authentication for push ──
    _setup_push_auth(repo_path)

    # Push to remote (force push to handle diverged branches)
    push_result = subprocess.run(
        ["git", "push", "--force", "-u", "origin", branch_name],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=60,
    )

    push_success = push_result.returncode == 0
    if push_success:
        print(f"[GIT] Push successful: {branch_name}")
    else:
        print(f"[GIT] Push failed: {push_result.stderr.strip()} | stdout: {push_result.stdout.strip()}")

    return {
        "success": True,
        "commit_hash": commit_hash[:8],
        "branch": branch_name,
        "push_success": push_success,
        "push_message": push_result.stderr if not push_success else "Pushed successfully",
    }


def _setup_push_auth(repo_path: str):
    """
    Configure git authentication for push.
    
    Strategy:
      1. If GITHUB_TOKEN is set, embed it in the remote URL
      2. Otherwise, try to use GitHub CLI as credential helper
    """
    github_token = os.environ.get("GITHUB_TOKEN", "")

    if github_token:
        # Method 1: Embed token in remote URL
        print("[GIT] Using GITHUB_TOKEN for authentication")
        # Get current remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        remote_url = result.stdout.strip()

        # Convert https://github.com/user/repo to https://<token>@github.com/user/repo
        if remote_url.startswith("https://") and "@" not in remote_url:
            auth_url = remote_url.replace("https://", f"https://{github_token}@")
            subprocess.run(
                ["git", "remote", "set-url", "origin", auth_url],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            print("[GIT] Remote URL updated with token")
    else:
        # Method 2: Use GitHub CLI as credential helper
        try:
            result = subprocess.run(
                ["gh", "auth", "setup-git"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                print("[GIT] GitHub CLI credential helper configured")
            else:
                print(f"[GIT] gh auth setup-git failed: {result.stderr}")
        except FileNotFoundError:
            print("[GIT] GitHub CLI not found — push may fail without credentials")
        except subprocess.TimeoutExpired:
            print("[GIT] gh auth setup-git timed out")


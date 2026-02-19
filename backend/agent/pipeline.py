"""
Pipeline orchestrator: ties all agent modules together into a single flow.

OPTIMIZED: Two-pass fix strategy
  Pass 1: Deterministic fixes (SYNTAX, IMPORT, LINTING, INDENTATION) — no LLM
  Pass 2: LLM fixes (LOGIC, TYPE_ERROR) — only if errors remain after Pass 1

Every step prints verbose, human-readable output to the terminal AND emits
structured SSE events to the frontend for real-time progressive rendering.
"""

import os
import json
import time

from agent.clone import clone_repo
from agent.analyzer import analyze_repo
from agent.test_runner import run_tests
from agent.deterministic_fixer import detect_and_fix_deterministic
from agent.llm import ask_for_fixes
from agent.fixer import apply_fixes
from agent.git_ops import make_branch_name, create_branch, commit_and_push

# Default workspace for cloned repos
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
MAX_ITERATIONS = 5


# ═══════════════════════════════════════════════════════════════════
#  TERMINAL LOGGING HELPERS
# ═══════════════════════════════════════════════════════════════════

def _banner(text):
    """Print a large prominent banner."""
    width = 70
    print("\n" + "═" * width)
    print(f"  {text}")
    print("═" * width + "\n")


def _section(text):
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  >>> {text}")
    print(f"{'─' * 60}")


def _info(tag, message):
    """Print a tagged info line."""
    print(f"[PIPELINE] [{tag}] {message}")


def _print_block(title, content, max_lines=100):
    """Print a multiline block with box drawing."""
    lines = content.split("\n")
    truncated = len(lines) > max_lines
    lines = lines[:max_lines]

    print(f"\n[PIPELINE] ┌─── {title} ───")
    for line in lines:
        print(f"[PIPELINE] │ {line}")
    if truncated:
        print(f"[PIPELINE] │ ... (truncated, {len(content.split(chr(10)))} total lines)")
    print(f"[PIPELINE] └{'─' * 50}\n")


# ═══════════════════════════════════════════════════════════════════
#  FILE READER — reads source files from test error paths
# ═══════════════════════════════════════════════════════════════════

def _discover_source_files_from_errors(repo_path: str, errors: list) -> list:
    """
    Extract source file paths from test errors + discover all src/*.py files.
    This REPLACES the old ask_files_needed() LLM call entirely.
    """
    files = set()

    # 1. Extract files mentioned in test errors
    for err in errors:
        err_file = err.get("file", "")
        if err_file and not err_file.startswith("test") and not "/test_" in err_file:
            files.add(err_file)

    # 2. Also discover all source .py files (non-test files)
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".tox", "tests"}]
        for fname in filenames:
            if fname.endswith(".py") and not fname.startswith("test_") and not fname.endswith("_test.py"):
                rel = os.path.relpath(os.path.join(root, fname), repo_path).replace("\\", "/")
                files.add(rel)

    return sorted(files)


def read_file_contents(repo_path: str, file_paths: list) -> dict:
    """Read the contents of the specified files from the repo."""
    contents = {}
    for fp in file_paths:
        full_path = os.path.join(repo_path, fp)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    contents[fp] = f.read()
                _info("READ", f"Read {fp} ({len(contents[fp])} chars)")
            except Exception as e:
                contents[fp] = f"<Error reading file: {e}>"
                _info("ERROR", f"Error reading {fp}: {e}")
        else:
            _info("WARN", f"File not found: {fp}")
    return contents


# ═══════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run_pipeline(repo_url: str, team_name: str, leader_name: str,
                 status_callback=None, event_callback=None) -> dict:
    """
    Run the full CI/CD healing pipeline with two-pass fix strategy.

    Pass 1: Deterministic fixes (no LLM) — handles SYNTAX, IMPORT, LINTING, INDENTATION
    Pass 2: LLM fixes (if needed)       — handles LOGIC, TYPE_ERROR
    """
    start_time = time.time()
    result = {
        "repo_url": repo_url,
        "team_name": team_name,
        "leader_name": leader_name,
        "branch_name": "",
        "iterations": [],
        "total_failures_detected": 0,
        "total_fixes_applied": 0,
        "final_status": "RUNNING",
        "all_fixes": [],
        "time_taken": 0,
    }

    def update_status(msg):
        print(f"[PIPELINE] {msg}")
        if status_callback:
            status_callback(msg)

    def emit(event_type, data):
        """Emit an SSE event to the frontend."""
        if event_callback:
            event_callback(event_type, data)

    # Track whether pip install has been done
    deps_installed = False

    try:
        # ═══════════════════════════════════════════════════════════
        #  STEP 1: CLONE REPOSITORY
        # ═══════════════════════════════════════════════════════════
        _banner("STEP 1: CLONING REPOSITORY")
        _info("CLONE", f"Repository URL: {repo_url}")
        _info("CLONE", f"Team: {team_name} | Leader: {leader_name}")

        update_status("Cloning repository...")
        emit("step", {"step": "clone", "message": f"Cloning {repo_url}..."})

        repo_path = clone_repo(repo_url, WORKSPACE_DIR)
        _info("CLONE", f"Cloned to: {repo_path}")

        emit("clone", {
            "status": "success",
            "repo_url": repo_url,
            "repo_path": repo_path,
            "message": "Repository cloned successfully",
        })

        # ═══════════════════════════════════════════════════════════
        #  STEP 2: ANALYZE REPOSITORY (done ONCE, not every iteration)
        # ═══════════════════════════════════════════════════════════
        _banner("STEP 2: ANALYZING REPOSITORY STRUCTURE")
        update_status("Analyzing repository structure...")
        emit("step", {"step": "analyze", "message": "Analyzing repository structure..."})

        analysis = analyze_repo(repo_path)

        result["analysis"] = {
            "tree": analysis["tree"],
            "test_files": analysis["test_files"],
            "language": analysis["language"],
            "test_command": analysis["test_command"],
        }

        _info("ANALYZE", f"Language detected: {analysis['language']}")
        _info("ANALYZE", f"Test command: {analysis['test_command']}")
        _info("ANALYZE", f"Test files found: {len(analysis['test_files'])}")
        for tf in analysis["test_files"]:
            _info("ANALYZE", f"  - {tf}")

        _print_block("FILE STRUCTURE TREE", analysis["tree"])

        emit("analysis", {
            "tree": analysis["tree"],
            "test_files": analysis["test_files"],
            "language": analysis["language"],
            "test_command": analysis["test_command"],
        })

        # ═══════════════════════════════════════════════════════════
        #  STEP 3: CREATE BRANCH
        # ═══════════════════════════════════════════════════════════
        _banner("STEP 3: CREATING GIT BRANCH")
        branch_name = make_branch_name(team_name, leader_name)
        result["branch_name"] = branch_name
        _info("GIT", f"Branch name: {branch_name}")

        create_branch(repo_path, branch_name)
        _info("GIT", f"Checked out branch: {branch_name}")

        emit("branch", {
            "branch_name": branch_name,
            "message": f"Created and checked out branch: {branch_name}",
        })

        # ═══════════════════════════════════════════════════════════
        #  STEP 4: DETERMINISTIC FIX PASS (no LLM — fast & free)
        # ═══════════════════════════════════════════════════════════
        _banner("STEP 4: DETERMINISTIC FIX PASS (NO LLM)")
        update_status("Running deterministic bug detection (no LLM)...")
        emit("step", {"step": "deterministic", "message": "Running deterministic bug detection..."})

        det_result = detect_and_fix_deterministic(repo_path)

        if det_result["fixes"]:
            _info("DETERMINISTIC", f"Found {len(det_result['fixes'])} deterministic fixes")

            emit("fixes", {
                "iteration": 0,
                "fixes": det_result["fixes"],
                "commit_title": det_result["commit_title"],
                "message": f"Deterministic: {len(det_result['fixes'])} fixes (no LLM needed)",
                "is_deterministic": True,
            })

            # Apply deterministic fixes
            applied = apply_fixes(repo_path, det_result["fixes"])
            applied_count = sum(1 for f in applied if f["status"] == "applied")
            failed_count = sum(1 for f in applied if f["status"] == "failed")
            result["total_fixes_applied"] += applied_count
            result["all_fixes"].extend(applied)

            _info("DETERMINISTIC", f"Applied: {applied_count} | Failed: {failed_count}")

            emit("fix_applied", {
                "iteration": 0,
                "applied": applied_count,
                "failed": failed_count,
                "details": applied,
                "message": f"Deterministic: Applied {applied_count}/{len(applied)} fixes",
                "is_deterministic": True,
            })

            if applied_count > 0:
                # Commit deterministic fixes
                commit_msg = det_result["commit_title"]
                commit_result = commit_and_push(repo_path, commit_msg, branch_name)

                _info("GIT", f"Committed deterministic fixes: {commit_result.get('commit_hash', 'N/A')}")

                emit("commit", {
                    "iteration": 0,
                    "commit_hash": commit_result.get("commit_hash", ""),
                    "branch": commit_result.get("branch", ""),
                    "push_success": commit_result.get("push_success", False),
                    "commit_message": commit_msg,
                    "message": f"Committed deterministic fixes",
                    "is_deterministic": True,
                })

                # Record this as iteration 0
                result["iterations"].append({
                    "iteration": 0,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "DETERMINISTIC_FIX",
                    "passed": 0,
                    "failed": 0,
                    "fixes_applied": applied,
                    "commit": commit_result,
                    "is_deterministic": True,
                })
        else:
            _info("DETERMINISTIC", "No deterministic fixes needed")

        # ═══════════════════════════════════════════════════════════
        #  ITERATION LOOP (now only for LLM-requiring fixes)
        # ═══════════════════════════════════════════════════════════
        for iteration in range(1, MAX_ITERATIONS + 1):
            _banner(f"ITERATION {iteration}/{MAX_ITERATIONS}")

            emit("iteration_start", {
                "iteration": iteration,
                "max_iterations": MAX_ITERATIONS,
                "message": f"Starting iteration {iteration}/{MAX_ITERATIONS}",
            })

            iter_result = {
                "iteration": iteration,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "running",
                "passed": 0,
                "failed": 0,
                "errors": [],
                "fixes_applied": [],
            }

            # ─── Run tests ───
            _section(f"ITERATION {iteration} — RUNNING TESTS")
            update_status(f"Iteration {iteration}/{MAX_ITERATIONS}: Running tests...")
            emit("step", {"step": "testing", "iteration": iteration, "message": "Running test suite..."})

            test_results = run_tests(repo_path, analysis["test_command"], skip_deps=deps_installed)
            deps_installed = True  # Mark deps as installed after first run

            iter_result["passed"] = test_results["passed"]
            iter_result["failed"] = test_results["failed"]
            iter_result["errors"] = test_results["errors"]

            _info("TESTS", f"Passed: {test_results['passed']} | Failed: {test_results['failed']}")
            _info("TESTS", f"Errors found: {len(test_results['errors'])}")
            _print_block("RAW TEST OUTPUT", test_results["raw_output"], max_lines=50)

            if test_results["errors"]:
                _section("PARSED ERROR DETAILS")
                for i, err in enumerate(test_results["errors"], 1):
                    _info("ERROR", f"  #{i}: {err.get('test_name', '?')} | {err.get('file', '?')}:{err.get('line', '?')} | {err.get('error_message', '?')}")

            emit("test_result", {
                "iteration": iteration,
                "passed": test_results["passed"],
                "failed": test_results["failed"],
                "error_count": len(test_results["errors"]),
                "errors": test_results["errors"],
                "raw_output": test_results["raw_output"][:3000],
            })

            # If all pass, we're done!
            if test_results["failed"] == 0 and len(test_results["errors"]) == 0:
                iter_result["status"] = "PASSED"
                result["iterations"].append(iter_result)
                result["final_status"] = "PASSED"

                _banner(f"ALL TESTS PASSED ON ITERATION {iteration}!")
                update_status(f"All tests passed on iteration {iteration}!")

                emit("all_passed", {
                    "iteration": iteration,
                    "message": f"All tests passed on iteration {iteration}!",
                })
                break

            result["total_failures_detected"] += test_results["failed"] + len(test_results["errors"])

            # ─── Discover source files from errors (NO LLM CALL) ───
            _section(f"ITERATION {iteration} — DISCOVERING SOURCE FILES (NO LLM)")
            files_needed = _discover_source_files_from_errors(repo_path, test_results["errors"])

            _info("FILES", f"Discovered {len(files_needed)} source files:")
            for fn in files_needed:
                _info("FILES", f"  - {fn}")

            emit("files_needed", {
                "iteration": iteration,
                "files": files_needed,
                "message": f"Discovered {len(files_needed)} source files (no LLM needed)",
            })

            # ─── Read source files ───
            file_contents = read_file_contents(repo_path, files_needed)

            emit("file_contents", {
                "iteration": iteration,
                "files": {fp: content[:2000] for fp, content in file_contents.items()},
                "message": f"Read {len(file_contents)} files",
            })

            # ─── Ask LLM for fixes (only LOGIC/TYPE_ERROR remain) ───
            _section(f"ITERATION {iteration} — ASKING LLM FOR CODE FIXES")
            update_status(f"Iteration {iteration}: Asking LLM for fixes (LOGIC/TYPE_ERROR only)...")
            emit("step", {"step": "llm_fixes", "iteration": iteration, "message": "Asking LLM for code fixes..."})

            fix_response = ask_for_fixes(analysis["tree"], file_contents, test_results["errors"])

            if not fix_response["fixes"]:
                _info("WARN", "LLM returned NO fixes. Stopping pipeline.")
                iter_result["status"] = "NO_FIXES"
                result["iterations"].append(iter_result)
                result["final_status"] = "FAILED"
                update_status("No fixes could be generated. Stopping.")

                emit("no_fixes", {
                    "iteration": iteration,
                    "message": "LLM could not generate any fixes",
                })
                break

            _info("FIXES", f"LLM returned {len(fix_response['fixes'])} fixes")
            for i, fix in enumerate(fix_response["fixes"], 1):
                _info("FIXES", f"  #{i}: [{fix.get('bug_type', '?')}] {fix.get('file', '?')}:{fix.get('line', '?')} — {fix.get('description', '?')}")

            emit("fixes", {
                "iteration": iteration,
                "fixes": fix_response["fixes"],
                "commit_title": fix_response["commit_title"],
                "message": f"LLM generated {len(fix_response['fixes'])} fixes",
            })

            # ─── Apply fixes ───
            _section(f"ITERATION {iteration} — APPLYING FIXES")
            update_status(f"Iteration {iteration}: Applying {len(fix_response['fixes'])} fixes...")
            emit("step", {"step": "applying", "iteration": iteration, "message": f"Applying {len(fix_response['fixes'])} fixes..."})

            applied = apply_fixes(repo_path, fix_response["fixes"])
            iter_result["fixes_applied"] = applied

            applied_count = sum(1 for f in applied if f["status"] == "applied")
            failed_count = sum(1 for f in applied if f["status"] == "failed")
            result["total_fixes_applied"] += applied_count
            result["all_fixes"].extend(applied)

            _info("APPLY", f"Applied: {applied_count} | Failed: {failed_count}")

            emit("fix_applied", {
                "iteration": iteration,
                "applied": applied_count,
                "failed": failed_count,
                "details": applied,
                "message": f"Applied {applied_count}/{len(applied)} fixes",
            })

            if applied_count == 0:
                _info("WARN", "No fixes could be applied. Stopping pipeline.")
                iter_result["status"] = "NO_FIXES_APPLIED"
                result["iterations"].append(iter_result)
                result["final_status"] = "FAILED"
                update_status("No fixes could be applied. Stopping.")

                emit("no_fixes_applied", {
                    "iteration": iteration,
                    "message": "No fixes could be applied to the code",
                })
                break

            # ─── Commit & Push ───
            _section(f"ITERATION {iteration} — COMMITTING & PUSHING")
            update_status(f"Iteration {iteration}: Committing fixes...")
            emit("step", {"step": "committing", "iteration": iteration, "message": "Committing and pushing changes..."})

            commit_msg = fix_response["commit_title"]
            if not commit_msg.startswith("[AI-AGENT]"):
                commit_msg = f"[AI-AGENT] {commit_msg}"

            commit_result = commit_and_push(repo_path, commit_msg, branch_name)
            iter_result["commit"] = commit_result

            _info("GIT", f"Commit: {commit_result.get('commit_hash', 'N/A')} | Push: {commit_result.get('push_success', 'N/A')}")

            emit("commit", {
                "iteration": iteration,
                "commit_hash": commit_result.get("commit_hash", ""),
                "branch": commit_result.get("branch", ""),
                "push_success": commit_result.get("push_success", False),
                "commit_message": commit_msg,
                "message": f"Committed {commit_result.get('commit_hash', 'N/A')} and pushed to {branch_name}",
            })

            iter_result["status"] = "FIXED"
            result["iterations"].append(iter_result)

            _banner(f"ITERATION {iteration} COMPLETE — {applied_count} fixes applied, re-testing...")

            emit("iteration_complete", {
                "iteration": iteration,
                "fixes_applied": applied_count,
                "message": f"Iteration {iteration} complete — {applied_count} fixes applied. Re-testing...",
            })

            # NOTE: No redundant analyze_repo() call here — tree doesn't change meaningfully

        else:
            # Max iterations reached
            if result["final_status"] == "RUNNING":
                result["final_status"] = "MAX_ITERATIONS"
                _banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) REACHED — some errors may remain")

                emit("max_iterations", {
                    "max_iterations": MAX_ITERATIONS,
                    "message": f"Maximum iterations ({MAX_ITERATIONS}) reached. Some errors may remain.",
                })

    except Exception as e:
        result["final_status"] = "ERROR"
        result["error"] = str(e)
        _banner(f"PIPELINE ERROR: {e}")
        update_status(f"Error: {e}")

        import traceback
        traceback.print_exc()

        emit("error", {"message": str(e)})

    result["time_taken"] = round(time.time() - start_time, 2)

    # ═══════════════════════════════════════════════════════════════
    #  FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    _banner("PIPELINE COMPLETE — FINAL SUMMARY")
    _info("SUMMARY", f"Status:           {result['final_status']}")
    _info("SUMMARY", f"Iterations:       {len(result['iterations'])}")
    _info("SUMMARY", f"Total failures:   {result['total_failures_detected']}")
    _info("SUMMARY", f"Total fixes:      {result['total_fixes_applied']}")
    _info("SUMMARY", f"Branch:           {result.get('branch_name', 'N/A')}")
    _info("SUMMARY", f"Time taken:       {result['time_taken']}s")

    emit("done", {
        "final_status": result["final_status"],
        "total_iterations": len(result["iterations"]),
        "total_failures_detected": result["total_failures_detected"],
        "total_fixes_applied": result["total_fixes_applied"],
        "branch_name": result.get("branch_name", ""),
        "time_taken": result["time_taken"],
        "result": result,
    })

    return result

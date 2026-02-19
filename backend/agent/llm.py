"""LLM module for the CI/CD Healing Agent.

OPTIMIZED: Only used for LOGIC and TYPE_ERROR bugs that genuinely need
LLM reasoning. SYNTAX/IMPORT/LINTING/INDENTATION bugs are handled by
deterministic_fixer.py without any API calls.

Supports four modes:
  - Dummy mode      (USE_DUMMY_LLM=true):       Hardcoded responses, no API needed.
  - OpenRouter mode (LLM_PROVIDER=openrouter):   Calls OpenRouter API.
  - Cerebras mode   (LLM_PROVIDER=cerebras):     Calls Cerebras Cloud SDK.
  - Gemini mode     (LLM_PROVIDER=gemini):       Calls Google Gemini API.
"""

import os
import json
import re
import requests

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

# ╔══════════════════════════════════════════════════════════════════╗
# ║  CONFIGURATION                                                   ║
# ╚══════════════════════════════════════════════════════════════════╝

USE_DUMMY_LLM = os.environ.get("USE_DUMMY_LLM", "true").lower() == "true"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter").lower()  # "openrouter", "cerebras", or "gemini"

# OpenRouter settings
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "sk-REPLACE-ME")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Cerebras settings
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")

# Gemini settings
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Logs directory
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
#  LOGGING HELPERS
# ═══════════════════════════════════════════════════════════════════

def _save_to_log(label: str, prompt: str, response: str):
    """Save a prompt+response pair to a timestamped log file."""
    import time
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}_{label}.txt"
    filepath = os.path.join(LOGS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"  LABEL: {label}\n")
        f.write(f"  TIME:  {timestamp}\n")
        f.write(f"  MODE:  {'DUMMY' if USE_DUMMY_LLM else LLM_PROVIDER.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(">>> PROMPT SENT TO LLM:\n")
        f.write("-" * 80 + "\n")
        f.write(prompt + "\n")
        f.write("-" * 80 + "\n\n")
        f.write("<<< RESPONSE FROM LLM:\n")
        f.write("-" * 80 + "\n")
        f.write(response + "\n")
        f.write("-" * 80 + "\n")

    _log("SAVE", f"Prompt+response saved to: logs/{filename}")


def _log(tag, message):
    print(f"[LLM] [{tag}] {message}")


def _log_block(tag, title, content):
    separator = "─" * 70
    print(f"\n[LLM] [{tag}] ┌{separator}")
    print(f"[LLM] [{tag}] │ {title}")
    print(f"[LLM] [{tag}] ├{separator}")
    for line in content.split("\n")[:50]:  # Limit output
        print(f"[LLM] [{tag}] │ {line}")
    print(f"[LLM] [{tag}] └{separator}\n")


SYSTEM_PROMPT = (
    "You are a code-fixing AI. Analyze test errors and source code, "
    "return precise fixes in the exact JSON format requested. "
    "ONLY return valid JSON — no markdown, no explanation."
)


# ═══════════════════════════════════════════════════════════════════
#  LLM CALL DISPATCHER
# ═══════════════════════════════════════════════════════════════════

def _call_llm(prompt: str) -> str:
    """Route the prompt to the configured LLM provider."""
    _log("PROVIDER", f"Using LLM provider: {LLM_PROVIDER.upper()}")
    _log_block("SEND", f"PROMPT BEING SENT TO LLM ({LLM_PROVIDER.upper()})", prompt)

    if LLM_PROVIDER == "cerebras":
        return _call_cerebras(prompt)
    elif LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    else:
        return _call_openrouter(prompt)


# ═══════════════════════════════════════════════════════════════════
#  CEREBRAS API CALL
# ═══════════════════════════════════════════════════════════════════

def _call_cerebras(prompt: str) -> str:
    """Send a prompt to Cerebras Cloud SDK and return the streamed response."""
    from cerebras.cloud.sdk import Cerebras

    _log("API", f"Calling Cerebras model: {CEREBRAS_MODEL}")

    client = Cerebras(api_key=CEREBRAS_API_KEY)

    retries = 3
    backoff = 2

    for attempt in range(retries):
        try:
            stream = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=CEREBRAS_MODEL,
                stream=True,
                max_completion_tokens=20000,
                temperature=0.7,
                top_p=0.8,
            )

            # Collect streamed chunks
            reply_parts = []
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    reply_parts.append(delta)

            reply = "".join(reply_parts)
            _log_block("RECV", "RESPONSE FROM CEREBRAS", reply)
            return reply

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                if attempt < retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    _log("WARN", f"Cerebras rate limited. Retrying in {sleep_time}s...")
                    import time
                    time.sleep(sleep_time)
                    continue
            _log("ERROR", f"Cerebras API call failed: {e}")
            raise RuntimeError(f"Cerebras API call failed: {e}")


# ═══════════════════════════════════════════════════════════════════
#  GEMINI API CALL
# ═══════════════════════════════════════════════════════════════════

def _call_gemini(prompt: str) -> str:
    """Send a prompt to Google Gemini API and return the response."""
    _log("API", f"Calling Gemini model: {GEMINI_MODEL}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }

    retries = 3
    backoff = 2

    for attempt in range(retries):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )

            if response.status_code == 429:
                if attempt < retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    _log("WARN", f"Gemini rate limited (429). Retrying in {sleep_time}s...")
                    import time
                    time.sleep(sleep_time)
                    continue
                else:
                    raise RuntimeError("Gemini rate limit exceeded (429).")

            response.raise_for_status()

            data = response.json()
            # Gemini response format: candidates[0].content.parts[0].text
            reply = data["candidates"][0]["content"]["parts"][0]["text"]

            _log_block("RECV", "RESPONSE FROM GEMINI", reply)
            return reply

        except requests.exceptions.RequestException as e:
            _log("ERROR", f"Gemini API call failed: {e}")
            raise RuntimeError(f"Gemini API call failed: {e}")
        except (KeyError, IndexError) as e:
            _log("ERROR", f"Unexpected Gemini response format: {e}")
            _log("ERROR", f"Raw response: {response.text[:500]}")
            raise RuntimeError(f"Gemini returned unexpected response format: {e}")


# ═══════════════════════════════════════════════════════════════════
#  OPENROUTER API CALL
# ═══════════════════════════════════════════════════════════════════

def _call_openrouter(prompt: str) -> str:
    """Send a prompt to OpenRouter and return the response."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ci-cd-agent",
        "X-Title": "CI/CD Healing Agent",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    _log("API", f"Calling OpenRouter model: {OPENROUTER_MODEL}")

    retries = 3
    backoff = 2

    for attempt in range(retries):
        try:
            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 429:
                if attempt < retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    _log("WARN", f"Rate limited (429). Retrying in {sleep_time}s...")
                    import time
                    time.sleep(sleep_time)
                    continue
                else:
                    raise RuntimeError("OpenRouter rate limit exceeded (429).")

            response.raise_for_status()

            data = response.json()
            reply = data["choices"][0]["message"]["content"]

            _log_block("RECV", "RESPONSE FROM OPENROUTER", reply)
            return reply

        except requests.exceptions.RequestException as e:
            _log("ERROR", f"OpenRouter API call failed: {e}")
            raise RuntimeError(f"LLM API call failed: {e}")


def _extract_json(text: str) -> dict:
    """Extract and parse JSON from LLM response text."""
    _log("PARSE", "Extracting JSON from response...")

    # Try code blocks first
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block:
        json_str = code_block.group(1).strip()
    else:
        json_str = text.strip()

    try:
        parsed = json.loads(json_str)
        _log("PARSE", f"Successfully parsed JSON with keys: {list(parsed.keys())}")
        return parsed
    except json.JSONDecodeError as e:
        _log("ERROR", f"Failed to parse JSON: {e}")
        _log("ERROR", f"Raw text was: {json_str[:500]}")
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")


# ═══════════════════════════════════════════════════════════════════
#  DUMMY (HARDCODED) RESPONSES — for testing without API
# ═══════════════════════════════════════════════════════════════════

def _dummy_ask_for_fixes() -> dict:
    """Return hardcoded fixes for common LOGIC/TYPE_ERROR bugs."""
    _log("DUMMY", "Using hardcoded fixes (USE_DUMMY_LLM = True)")
    result = {
        "fixes": [
            {
                "file": "src/utils.py",
                "line": 59,
                "old_code": "    return n + factorial(n - 1)  # LOGIC ERROR line 53: uses + instead of * — gives wrong result",
                "new_code": "    return n * factorial(n - 1)",
                "bug_type": "LOGIC",
                "description": "Fix factorial: should use '*' not '+'",
            },
            {
                "file": "src/config.py",
                "line": 49,
                "old_code": "        return port  # should be: return int(port)",
                "new_code": "        return int(port)",
                "bug_type": "TYPE_ERROR",
                "description": "Fix get_port: cast to int to handle string from env var",
            },
            {
                "file": "src/data_processor.py",
                "line": 26,
                "old_code": "    return [item for item in data if item.get(\"value\", 0) < threshold]",
                "new_code": "    return [item for item in data if item.get(\"value\", 0) > threshold]",
                "bug_type": "LOGIC",
                "description": "Fix filter_by_value: should use '>' not '<' for above threshold",
            },
        ],
        "commit_title": "[AI-AGENT] Fix logic and type errors",
    }
    _log("DUMMY", f"Returning {len(result['fixes'])} hardcoded fixes")
    return result


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC API — called by pipeline.py
# ═══════════════════════════════════════════════════════════════════

def ask_for_fixes(tree_str: str, file_contents: dict, errors: list) -> dict:
    """
    Given the repo tree, file contents, and test errors, ask for specific
    line-level code fixes. Only called for LOGIC/TYPE_ERROR bugs that
    can't be fixed deterministically.

    Returns:
        dict with keys:
          - fixes: list of {file, line, old_code, new_code, bug_type, description}
          - commit_title: string for the git commit message
    """
    _log("STEP", "=" * 60)
    _log("STEP", "ASKING LLM FOR CODE FIXES (LOGIC/TYPE_ERROR only)")
    _log("STEP", "=" * 60)

    # ── Dummy mode ──
    if USE_DUMMY_LLM:
        dummy_result = _dummy_ask_for_fixes()
        _save_to_log("ask_for_fixes", "(DUMMY MODE — no prompt sent)", json.dumps(dummy_result, indent=2))
        return dummy_result

    # ── Real LLM mode ──
    errors_text = "\n".join(
        f"  - Test: {e.get('test_name', 'unknown')} | File: {e.get('file', '?')} | "
        f"Line: {e.get('line', '?')} | Error: {e.get('error_message', '?')}"
        for e in errors
    )

    files_text = ""
    for filepath, content in file_contents.items():
        files_text += f"\n--- FILE: {filepath} ---\n{content}\n"

    prompt = f"""You are a code-fixing AI. Here are the test errors:

{errors_text}

Here are the source files:

{files_text}

For each bug, provide a fix.

Respond ONLY with valid JSON:
{{
  "fixes": [
    {{
      "file": "relative/path/to/file.py",
      "line": <line_number>,
      "old_code": "<exact current line>",
      "new_code": "<corrected line>",
      "bug_type": "<SYNTAX|LOGIC|IMPORT|LINTING|TYPE_ERROR|INDENTATION|OTHER>",
      "description": "<short description>"
    }}
  ],
  "commit_title": "[AI-AGENT] <summary of fixes>"
}}

IMPORTANT:
- "old_code" must match the EXACT current line (whitespace matters).
- "new_code" is the replacement. Use "" to delete a line.
- Include ALL fixes needed.
"""

    response_text = _call_llm(prompt)
    _save_to_log("ask_for_fixes", prompt, response_text)
    parsed = _extract_json(response_text)

    fixes = parsed.get("fixes", [])
    commit_title = parsed.get("commit_title", "[AI-AGENT] Auto-fix errors")

    _log("RESULT", f"LLM returned {len(fixes)} fixes:")
    for i, fix in enumerate(fixes, 1):
        _log("RESULT", f"  #{i}: [{fix.get('bug_type', '?')}] {fix.get('file', '?')}:{fix.get('line', '?')} — {fix.get('description', '')}")

    return {"fixes": fixes, "commit_title": commit_title}

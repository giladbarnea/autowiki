#!/bin/bash
# Claude Code status line script.
# Reads JSON from stdin and prints a single formatted status line (first line of stdout).
# https://code.claude.com/docs/en/statusline
#
# Example JSON:
# {
#   "hook_event_name": "Status",
#   "session_id": "10f3a7f8-6659-4c03-ba74-83a50f2e31c8",
#   "transcript_path": "/Users/giladbarnea/.claude/projects/-Users-giladbarnea-dev-gchat/10f3a7f8-6659-4c03-ba74-83a50f2e31c8.jsonl",
#   "cwd": "/Users/giladbarnea/dev/gchat",
#   "model": {
#     "id": "claude-opus-4-5-20251101",
#     "display_name": "Opus 4.5"
#   },
#   "workspace": {
#     "current_dir": "/Users/giladbarnea/dev/gchat",
#     "project_dir": "/Users/giladbarnea/dev/gchat"
#   },
#   "version": "2.0.76",
#   "output_style": {
#     "name": "default"
#   },
#   "cost": {
#     "total_cost_usd": 9.247066450000002,
#     "total_duration_ms": 18500770,
#     "total_api_duration_ms": 861851,
#     "total_lines_added": 653,
#     "total_lines_removed": 79
#   },
#   "context_window": {
#     "total_input_tokens": 473122,
#     "total_output_tokens": 40730,
#     "context_window_size": 200000,
#     "current_usage": {
#       "input_tokens": 8,
#       "output_tokens": 30,
#       "cache_creation_input_tokens": 134,
#       "cache_read_input_tokens": 104374
#     }
#   },
#   "exceeds_200k_tokens": false
# }

CLAUDE_STATUSLINE_JSON="$(cat)"
export CLAUDE_STATUSLINE_JSON

# Detect available Python (3.13 preferred, cascade down to 3.9)
PYTHON=""
for _ver in python3.13 python3.12 python3.11 python3.10 python3.9; do
  if command -v "$_ver" >/dev/null 2>&1; then
    PYTHON="$_ver"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "[ERROR][statusline.sh] No compatible Python (3.9–3.13) found in PATH" | tee /dev/stderr
  exit 1
fi

# Compute git branch in shell (no Python subprocess). We need cwd from the JSON.
CLAUDE_STATUSLINE_CWD="$(
  $PYTHON -OBIS - <<'PY'
import json, os
raw = os.environ.get('CLAUDE_STATUSLINE_JSON', '')
try:
    data = json.loads(raw) if raw else {}
except Exception:
    data = {}
print(data.get('cwd') or '.')
PY
)"

ORIGINAL_CWD=$(pwd)
# Use the JSON cwd for git operations.
if [ -n "$CLAUDE_STATUSLINE_CWD" ]; then
  builtin cd "$CLAUDE_STATUSLINE_CWD" 2>/dev/null || true
fi

CLAUDE_GIT_BRANCH=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  BRANCH="$(git branch --show-current 2>/dev/null)"
  if [ -n "$BRANCH" ]; then
    CLAUDE_GIT_BRANCH=" $BRANCH "
  fi
fi
export CLAUDE_GIT_BRANCH

IS_GIT_DIR_DIRTY=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && {
  ! git diff --quiet HEAD 2>/dev/null ||
    ! git diff --cached --quiet 2>/dev/null ||
    [[ -n "$(git ls-files --others --exclude-standard)" ]]
}; then
  IS_GIT_DIR_DIRTY="*"
fi
export IS_GIT_DIR_DIRTY

CLAUDE_TRANSCRIPT_PATH="$(echo "$CLAUDE_STATUSLINE_JSON" | jq -r '.transcript_path // empty')"

CLAUDE_SESSION_ID="$(echo "$CLAUDE_STATUSLINE_JSON" | jq -r '.session_id // empty')"
export CLAUDE_SESSION_ID

# Mark whether exists in sessions.yaml in the session’s cwd
CLAUDE_SESSION_EXISTS_IN_SESSIONS_YAML=""
if [ -n "$CLAUDE_STATUSLINE_CWD" ]; then
  if [ -f "$CLAUDE_STATUSLINE_CWD/sessions.yaml" ]; then
    if yq -e ".sessions.$CLAUDE_SESSION_ID != null" "$CLAUDE_STATUSLINE_CWD/sessions.yaml" >/dev/null 2>&1; then
      CLAUDE_SESSION_EXISTS_IN_SESSIONS_YAML="true"
    fi
  fi
fi
export CLAUDE_SESSION_EXISTS_IN_SESSIONS_YAML

# Count the number of text messages in the session with `jq -s 'map(select((.message.role == "assistant" and .message.content[0].type == "text") or (.type == "user" and (.message.content | type) == "string"))) | length' $CLAUDE_TRANSCRIPT_PATH`
CLAUDE_SESSION_MESSAGE_COUNT=""
if [ -n "$CLAUDE_TRANSCRIPT_PATH" ] && [ -f "$CLAUDE_TRANSCRIPT_PATH" ]; then
  CLAUDE_SESSION_MESSAGE_COUNT="$(jq -s 'map(select((.message.role == "assistant" and .message.content[0].type == "text") or (.type == "user" and (.message.content | type) == "string"))) | length' "$CLAUDE_TRANSCRIPT_PATH")"
fi
export CLAUDE_SESSION_MESSAGE_COUNT

# Get the `updated_when_message_count_was` from the session in sessions.yaml with `yq .sessions.45565f09-3c6a-4460-b43c-5ff5c2171caf.updated_when_message_count_was sessions.yaml`
CLAUDE_SESSION_CATALOG_LAST_UPDATED_MESSAGE_COUNT=""
if [ -n "$CLAUDE_SESSION_ID" ] && [ -n "$CLAUDE_STATUSLINE_CWD" ]; then
  if [ -f "$CLAUDE_STATUSLINE_CWD/sessions.yaml" ]; then
    CLAUDE_SESSION_CATALOG_LAST_UPDATED_MESSAGE_COUNT="$(yq ".sessions.$CLAUDE_SESSION_ID.updated_when_message_count_was // 0" "$CLAUDE_STATUSLINE_CWD/sessions.yaml")"
  fi
fi
export CLAUDE_SESSION_CATALOG_LAST_UPDATED_MESSAGE_COUNT

builtin cd "$ORIGINAL_CWD" 2>/dev/null || true
$PYTHON -OBIS - <<'PY'
import json
import os
from pathlib import Path
BLACK = '\x1b[30m'
DIM = '\x1b[2m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
RESET = '\x1b[0m'

raw = os.environ.get("CLAUDE_STATUSLINE_JSON", "")
try:
    data = json.loads(raw) if raw else {}
except Exception:
    data = {}

home = os.environ.get("HOME") or str(Path.home())

def shorten_path(p: str) -> str:
    if not p:
        return "."
    if home and p.startswith(home):
        rest = p[len(home):]
        return "~" + (rest if rest else "")
    return p

def format_tokens(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        n = 0
    if n >= 1_000_000:
        return f"{n // 1_000_000:,}M"
    if n >= 1_000:
        return f"{n // 1_000:,}k"
    return str(n)

def clamp_int(n, lo: int, hi: int) -> int:
    try:
        n = int(n)
    except Exception:
        return lo
    return lo if n < lo else hi if n > hi else n

def ctx_gauge(pct: int) -> str:
    # Single-character "fill" gauge (low → high): ▏▎▍▌▋▊▉█
    pct = clamp_int(pct, 0, 100)
    blocks = "▏▎▍▌▋▊▉█"
    idx = int((pct / 100) * (len(blocks) - 1))
    return blocks[idx]

def heat_color(pct: int) -> str:
    """Return RGB color transitioning green → yellow → red based on percentage."""
    pct = clamp_int(pct, 0, 100)
    if pct <= 50:
        # Green (0,255,0) → Yellow (255,255,0)
        r = int((pct / 50) * 255)
        g = 255
    else:
        # Yellow (255,255,0) → Red (255,0,0)
        r = 255
        g = int((1 - (pct - 50) / 50) * 255)
    return f'\x1b[38;2;{r};{g};0m'

# --[ Session ID ]--
session_id = data.get("session_id") or "N/A"
parts = [f"\x1b[97m{session_id}\x1b[0m"]

# --[ CWD ]--
cwd_raw = data.get("cwd") or "."
# Paint in plain bright blue the cwd (the two-digit code for bright blue)
parts.append(f"\x1b[34m {shorten_path(cwd_raw)}\x1b[0m")


# --[ Git Branch ]--
branch = os.environ.get("CLAUDE_GIT_BRANCH") or ""
is_git_dir_dirty = os.environ.get("IS_GIT_DIR_DIRTY") or ""
if branch.strip():
    parts.append(f"\x1b[33m {branch.strip()} {is_git_dir_dirty}\x1b[0m")

# --[ Model ]--
model = (data.get("model") or {}).get("display_name") or "N/A"
model_icon = "◈" if "opus" in model.lower() else "◇"
parts.append(f"\x1b[36m{model_icon} {model}\x1b[0m")

# --[ Cataloged ]--
session_exists_in_sessions_yaml = os.environ.get("CLAUDE_SESSION_EXISTS_IN_SESSIONS_YAML") or ""
session_message_count = int(os.environ.get("CLAUDE_SESSION_MESSAGE_COUNT") or 0)
cataloged_message_count = int(os.environ.get("CLAUDE_SESSION_CATALOG_LAST_UPDATED_MESSAGE_COUNT") or 0)
def magenta(string):
    return f"\x1b[35m{string}\x1b[0m"
if session_exists_in_sessions_yaml.strip():
    if cataloged_message_count > 0 and cataloged_message_count == session_message_count:
        parts.append(magenta(f"Cataloged: {session_message_count}/{cataloged_message_count}"))
    else:
        # Use star for "dirty".
        parts.append(magenta(f"Cataloged *: {session_message_count}/{cataloged_message_count}"))
elif session_message_count > 0:
    # Use -- for "not cataloged"
    parts.append(magenta("Cataloged: --"))

# --[ Cost ]--
cost = (data.get("cost") or {}).get("total_cost_usd")
parts.append("$" + ("0" if cost is None else f"{cost:,.1f}"))

# --[ Context Window ]--
context_window = data.get("context_window") or {}
# Use current_usage to show actual context window utilization
current_usage = context_window.get("current_usage") or {}
input_tokens = current_usage.get("input_tokens") or 0
cache_creation = current_usage.get("cache_creation_input_tokens") or 0
cache_read = current_usage.get("cache_read_input_tokens") or 0
used = input_tokens + cache_creation + cache_read
context_str = None
if used:
    total = context_window.get("context_window_size") or 200_000
    try:
        pct = int((used / total) * 100) if total else 0
    except Exception:
        pct = 0
    color = heat_color(pct)
    gauge = ctx_gauge(pct)
    context_str = f"{color}{gauge}{RESET} {format_tokens(used)}/{format_tokens(total)} ({color}{pct}%{RESET})"

if context_str:
    parts.append(context_str)

seperator = f" {BLACK}{DIM}│{RESET} "
dimmed_parts = [DIM + p + RESET for p in parts if p]
print(seperator.join(dimmed_parts))
PY

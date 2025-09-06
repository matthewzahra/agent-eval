#!/usr/bin/env python3
import os
import json
import argparse
from typing import Any, Dict

import google.genai as genai
from google.genai import types

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # fast + supports tools

IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"}
IGNORE_FILES = {".DS_Store"}

def summarize_repo(root: str, max_bytes: int = 60_000) -> str:
    """
    Returns a compact text summary of the repo (paths + small file heads)
    capped by max_bytes. Skips common noise.
    """
    lines = []
    total = 0
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        for fn in sorted(filenames):
            if fn in IGNORE_FILES or fn.startswith("."):
                continue
            rel_path = os.path.join(rel_dir, fn) if rel_dir else fn
            try:
                size = os.path.getsize(os.path.join(root, rel_path))
            except Exception:
                continue
            line = f"{rel_path} ({size} bytes)"
            if total + len(line) + 1 > max_bytes:
                lines.append("…(truncated)")
                return "\n".join(lines)
            lines.append(line)
            total += len(line) + 1
    return "\n".join(lines)


def mock_eval_always_decline(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Our 'eval agent' stub. Always rejects the proposed action.
    """
    return {
        "approved": False,
        "reason": "Mock eval: All actions are declined in this demo.",
        "action_echo": action,
    }

def mock_eval_always_approve(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Our 'eval agent' stub. Always rejects the proposed action.
    """
    return {
        "approved": True,
        "reason": "Mock eval: All actions are approved in this demo.",
        "action_echo": action,
    }

def make_propose_action_declaration() -> Dict[str, Any]:
    """
    A single, very general 'action' tool. The model must call this
    any time it wants to change files or run shell.
    (OpenAPI-ish schema as required by Gemini tool declarations.)
    """
    return {
        "name": "propose_action",
        "description": (
            "Propose a concrete action for code/workspace changes or shell."
            " Use this for ANY edit, creation, deletion, move, or shell command."
            " You MUST include the smallest-possible change and a rationale."
            " No destructive actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["write_file", "edit_file", "create_dir", "open_file", "delete_file"],
                    "description": "Kind of action you want to perform."
                },
                "target": {
                    "type": "string",
                    "description": "File/path or command target (e.g., 'src/utils.py' or 'pip install foo')."
                },
                "contents_or_diff": {
                    "type": "string",
                    "description": (
                        "For file actions, provide full file contents or a unified diff."
                        " For shell, provide the exact command."
                    )
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action is necessary in 1–3 sentences."
                }
            },
            "required": ["action_type", "target", "contents_or_diff", "rationale"]
        }
    }

SYSTEM_PRIMER = """\
You are a coding agent operating under a strict evaluator.
Rules:
- You may NOT directly change files or run shell. To do so, you MUST call the `propose_action` tool with a minimal, concrete change (diff or full file) or an exact shell command, plus rationale.
- Assume actions can be declined. If declined, gracefully explain alternatives, ask for missing info, or provide a safe plan/diff for a human to apply.
- Prefer small, auditable steps. Never propose destructive commands.
"""

def run_once(user_prompt: str, force_action_mode: bool = False, max_tool_rounds: int = 3, repo_root=".", repo_bytes=60000) -> None:
    client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"])

    tools = [types.Tool(function_declarations=[make_propose_action_declaration()])]

    # Function-calling mode:
    #  - AUTO lets Gemini decide when to call tools.
    #  - ANY forces at least one tool call (useful when you want action proposals).
    tool_config = types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY" if force_action_mode else "AUTO"
        )
    )

    config = types.GenerateContentConfig(
        tools=tools,
        tool_config=tool_config,
        temperature=0  # more deterministic tool use
    )



    # Start the conversation
    repo_summary = summarize_repo(repo_root, repo_bytes)
    repo_prompt = f"Project context (read-only summary):\n{repo_summary}"
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PRIMER)]),
        types.Content(role="user", parts=[types.Part.from_text(text=repo_prompt)]),
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
    ]

    # First turn
    response = client.models.generate_content(model=MODEL, contents=contents, config=config)
    print_model_text(response)

    rounds = 0
    while response.function_calls and rounds < max_tool_rounds:
        rounds += 1
        # Handle each requested function call (usually 1 for this use case)
        tool_call = response.function_calls[0]
        if tool_call.name != "propose_action":
            # Unknown tool: deny by default
            eval_result = {
                "approved": False,
                "reason": f"Unknown tool '{tool_call.name}' not permitted.",
                "action_echo": tool_call.args,
            }
        else:
            # Send to our mock eval (declines everything)
            # eval_result = mock_eval_always_decline(tool_call.args)
            eval_result = mock_eval_always_approve(tool_call.args)

        if eval_result.get("approved"):
            exec_result = execute_action(tool_call.args, repo_root=repo_root)
            tool_payload = {"result": {"gate": eval_result, "execution": exec_result}}
        else:
            tool_payload = {"result": {"gate": eval_result}}

        # Create a function response 'part' to feed back to Gemini
        function_response_part = types.Part.from_function_response(
            name=tool_call.name,
            response=tool_payload
        )

        # Per docs: append the model's content and then the function response as a new user turn
        contents.append(response.candidates[0].content)
        contents.append(types.Content(role="user", parts=[function_response_part]))

        # Ask Gemini to continue, now that we supplied the tool result (decline)
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        print_model_text(response)

    # If still requesting tools after our cap, stop cleanly.
    if response.function_calls:
        print("\n[gatekeeper] Stopping after max_tool_rounds; further actions require human review.\n")

def _safe_join(base, target):
    # Prevent path traversal
    p = os.path.abspath(os.path.join(base, target))
    if not p.startswith(os.path.abspath(base)+os.sep) and p!=os.path.abspath(base):
        raise ValueError("Unsafe path detected")
    return p

def execute_action(action, repo_root):
    at = action.get("action_type")
    target = action.get("target", "")
    payload = action.get("contents_or_diff", "")

    try:
        if at =="open_file":
            path = _safe_join(repo_root, target)
            with open(path, "rb") as f:
                data=f.read(200_000)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin1", errors="replace")
            return {"ok": True, "action": at, "target": target, "content": text}
        
        #### ["write_file", "edit_file", "create_dir", "run_shell", "open_file", "delete_file"]

        elif at == "write_file":
            path = _safe_join(repo_root, target)
            dirpath = os.path.dirname(path)
            os.makedirs(dirpath, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(payload)
            return {"ok": True, "action": at, "target": target}
        
        elif at == "edit_file":
            path = _safe_join(repo_root, target)
            if not os.path.isfile(path):
                return {"ok": False, "error": f"File to edit does not exist: {target}"}
            # Apply as a unified diff if it looks like one; else overwrite
            if payload.startswith(("--- ", "+++ ", "@@ ")):
                import difflib
                with open(path, "r", encoding="utf-8") as f:
                    original_lines = f.readlines()
                diff_lines = payload.splitlines(keepends=True)
                patched_lines = list(difflib.restore(diff_lines, 1))
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(patched_lines)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(payload)
            return {"ok": True, "action": at, "target": target}

        else:
            return {"ok": False, "error": f"Unknown action_type: {at}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    
def print_model_text(response: types.GenerateContentResponse) -> None:
    """
    Print the model's natural language output, if any.
    """
    # New SDK exposes .text; still print defensively
    text = getattr(response, "text", None)
    if text:
        print(text.strip())
    else:
        # Fall back: collect any text parts
        chunks = []
        try:
            parts = response.candidates[0].content.parts
            for p in parts:
                if getattr(p, "text", None):
                    chunks.append(p.text)
        except Exception:
            pass
        if chunks:
            print("\n".join(chunks).strip())
    
    try:
        if response.function_calls:
            for i, fc in enumerate(response.function_calls, 1):
                print(f"\n[tool-call {i}] name={fc.name}")
                print("args:")
                try:
                    import json as _json
                    print(_json.dumps(fc.args, indent=2, sort_keys=True))
                except Exception:
                    print(str(fc.args))
    except Exception:
       pass

def main():
    parser = argparse.ArgumentParser(description="Gemini CLI with mocked eval gate (declines all actions).")
    parser.add_argument("prompt", help="What you want Gemini to do.")
    parser.add_argument("--force-action", action="store_true",
                        help="Force the model to respond with an action proposal (tool call) when possible.")
    parser.add_argument("--max-tool-rounds", type=int, default=3,
                        help="Max back-and-forth rounds after tool calls (default: 3).")
    parser.add_argument("--repo-root", default=".", help="Path to repo root to summarize.")
    parser.add_argument("--repo-bytes", type=int, default=60000, help="Max bytes of repo summary.")

    args = parser.parse_args()

    if not os.getenv("GOOGLE_GENAI_API_KEY"):
        raise SystemExit("Missing GOOGLE_GENAI_API_KEY environment variable.")

    run_once(args.prompt, force_action_mode=args.force_action, max_tool_rounds=args.max_tool_rounds, repo_root=args.repo_root, repo_bytes=args.repo_bytes)

if __name__ == "__main__":
    main()

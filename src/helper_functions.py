from google.genai import types
import json as _json
import os 


def print_model_text(response: types.GenerateContentResponse) -> list[str]:
    """
    Print the model's natural language output, if any.
    Returns any function calls made - since this is what we want to return to the user via the webpage. 
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
    res = []
    try:
        if response.function_calls:
            for i, fc in enumerate(response.function_calls, 1):
                print(f"\n[tool-call {i}] name={fc.name}")
                print("args:")
                try:
                    res.append(_json.dumps(fc.args, indent=2, sort_keys=True))
                    print(_json.dumps(fc.args, indent=2, sort_keys=True))
                except Exception:
                    print(str(fc.args))
    except Exception:
       pass

    return res

def summarize_repo(root: str = '.', max_bytes: int = 60_000) -> str:
    IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"}
    IGNORE_FILES = {".DS_Store"}

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

if __name__ == '__main__':
    print(summarize_repo())
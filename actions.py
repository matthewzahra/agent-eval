from enum import Enum
import os

class Action(Enum):
    WRITE_FILE = "write_file"
    OPEN_FILE = "open_file"
    DELETE_FILE = "delete_file"


def execute_action(action: Action, target: str, repo_root: str, payload: str = ""):
    path = _safe_join(repo_root, target)
    try:
        if action==action.OPEN_FILE:
            with open(path, "rb") as f:
                data=f.read(200_000)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin1", errors="replace")
            return {"ok": True, "action": action, "target": target, "content": text}
        
        elif action==action.WRITE_FILE:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(payload)
            return {"ok": True, "action": action, "target": target}
        
        elif action==action.DELETE_FILE:
            path = _safe_join(repo_root, target)
            if os.path.exists(path):
                os.remove(path)
                return {"ok": True, "action": action, "target": target}
            else:
                return {"ok": False, "error": "File does not exist"}

        else:
            return {"ok": False, "error": f"Unknown action_type: {action}"}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _safe_join(base, target):
    # Prevent path traversal
    p = os.path.abspath(os.path.join(base, target))
    if not p.startswith(os.path.abspath(base)+os.sep) and p!=os.path.abspath(base):
        raise ValueError("Unsafe path detected")
    return p
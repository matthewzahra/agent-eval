from dataclasses import dataclass
import os 
import google.genai as genai
from google.genai import types
from config import SYSTEM_PRIMER, CHECK_STR, MODEL_EVAL, MODEL_ACTION
from helper_functions import print_model_text
from dotenv import load_dotenv
from actions import Action

load_dotenv()

@dataclass
class State:
    repo_state: dict
    


class Agent:
    model: str


class EvalAgent(Agent):
    '''
    we always allow it to read files 
    '''
    def __init__(self,goal):
        self.goal = goal
        self.current_state = None
        self.check_str = CHECK_STR # used to evaluate in the prompt
        self.client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"])

    def prompt(self,prompt,force_action_mode=True):
        tools = [types.Tool(function_declarations=[self.make_evaluation_response()])] 

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
            temperature=0.5  # more deterministic tool use
        )


        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=CHECK_STR)]),
            types.Content(role="user", parts=[types.Part.from_text(text=self.current_state)]),
            types.Content(role="user", parts=[types.Part.from_text(text=self.check_str.format(goal=self.goal, repo=self.current_state, action=prompt))]),
        ]
        response = self.client.models.generate_content(model=MODEL_EVAL, contents=contents, config=config)
        return print_model_text(response)
    
    def make_evaluation_response(self):
        return {
            "name": "evaluate_action",
            "description": (
                "Provide a gate decision on whether to approve or decline the proposed action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["approve", "decline"],
                        "description": "Whether to approve or decline the proposed action."
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this action is approved or declined, in 1–3 sentences."
                    }
                },
                "required": ["decision", "rationale"]
            }
        }

    def evaluate_action(self,action,target) -> bool:
        res = self.prompt(f'{self.check_str}. The agent is trying to perform the action: {action.name} on {target}')
        if res == 'True':
            return True
        return False


    def update_state(self,state) -> None:
        self.current_state = state 

class ActionAgent(Agent):
    def __init__(self):
    # allowed_actions: dict
    # context: dict
    # pre_amble:str
        self.client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"])


    def summarize_repo(self,root: str = '.', max_bytes: int = 60_000) -> str:
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

    def safe_join(self, base, target):
        # Prevent path traversal
        p = os.path.abspath(os.path.join(base, target))
        if not p.startswith(os.path.abspath(base)+os.sep) and p!=os.path.abspath(base):
            raise ValueError("Unsafe path detected")
        return p
    
    
    def execute_action(self, action: Action, target: str, repo_root: str = '.', payload: str = ""):
        path = self.safe_join(repo_root, target)
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
                if os.path.exists(path):
                    os.remove(path)
                    return {"ok": True, "action": action, "target": target}
                else:
                    return {"ok": False, "error": "File does not exist"}
                
            elif action==action.COMPLETED:
                return {"ok": True, "action": action, "target": target}

            else:
                return {"ok": False, "error": f"Unknown action_type: {action}"}
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
        



    def make_propose_action_declaration(self):
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
                        "enum": ["WRITE_FILE", "OPEN_FILE", "DELETE_FILE", "COMPLETED"],
                        "description": "Kind of action you want to perform."
                        "Completed is used when you are done and have no more actions."
                    },
                    "target": {
                        "type": "string",
                        "description": "File/path or command target (e.g., 'src/utils.py' or 'pip install foo')."
                    },
                    "contents_or_diff": {
                        "type": "string",
                        "description": (
                            "For file actions, provide full file contents or a unified diff."
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

    def prompt(self,user_prompt,force_action_mode=True, max_tool_rounds: int = 3):     # use the pre-amble
        tools = [types.Tool(function_declarations=[self.make_propose_action_declaration()])]

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
            temperature=0.5  # more deterministic tool use
        )

        # Start the conversation
        repo_summary = self.summarize_repo()
        repo_prompt = f"Project context (read-only summary):\n{repo_summary}"
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PRIMER)]),
            types.Content(role="user", parts=[types.Part.from_text(text=repo_prompt)]),
            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
        ]

        # First turn
        response = self.client.models.generate_content(model=MODEL_ACTION, contents=contents, config=config)
        res = print_model_text(response)

        # If still requesting tools after our cap, stop cleanly.
        if response.function_calls:
            print("\n[gatekeeper] Stopping after max_tool_rounds; further actions require human review.\n")

        return res

if __name__ == '__main__':
    prompt = ''
    agent = ActionAgent()
    state = agent.summarize_repo()
    eval_agent = EvalAgent(goal=prompt)
    eval_agent.current_state = state
    # res = agent.prompt('read the files')
    # print(res)

    # res_eval = eval_agent.prompt(prompt=res)
    # print(res_eval)

    agent.execute_action(Action["WRITE_FILE"], 'test.txt')
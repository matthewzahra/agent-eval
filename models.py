from dataclasses import dataclass
import os 
from typing import Optional
import google.genai as genai
from google.genai import types
from config import SYSTEM_PRIMER, MODEL, CHECK_STR
from helper_functions import print_model_text
from dotenv import load_dotenv

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
    def __init__(self,goal,check_str):
        self.goal = goal
        self.current_state = None
        self.check_str = check_str # used to evaluate in the prompt
        self.client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"])

    def prompt(self,prompt):
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=CHECK_STR)]),
            types.Content(role="user", parts=[types.Part.from_text(text=self.current_state)]),
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ]
        response = self.client.models.generate_content(model=MODEL, contents=contents) # TODO - config?
        return response


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
    
    def execute_action(self,action):
        ...
    
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
                        "enum": ["write_file", "edit_file", "create_dir", "run_shell", "open_file"],
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

    def prompt(self,user_prompt,force_action_mode=False, max_tool_rounds: int = 3):     # use the pre-amble
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
            temperature=0  # more deterministic tool use
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
        response = self.client.models.generate_content(model=MODEL, contents=contents, config=config)
        print_model_text(response)

        # rounds = 0
        # while response.function_calls and rounds < max_tool_rounds:
        #     rounds += 1
        #     # Handle each requested function call (usually 1 for this use case)
        #     tool_call = response.function_calls[0]
        #     if tool_call.name != "propose_action":
        #         # Unknown tool: deny by default
        #         eval_result = {
        #             "approved": False,
        #             "reason": f"Unknown tool '{tool_call.name}' not permitted.",
        #             "action_echo": tool_call.args,
        #         }
        #     else:
        #         # Send to our mock eval (declines everything)
        #         # eval_result = mock_eval_always_decline(tool_call.args)
        #         eval_result = mock_eval_always_approve(tool_call.args)

        #     if eval_result.get("approved"):
        #         exec_result = self.execute_action(tool_call.args, repo_root=repo_root)
        #         tool_payload = {"result": {"gate": eval_result, "execution": exec_result}}
        #     else:
        #         tool_payload = {"result": {"gate": eval_result}}

        #     # Create a function response 'part' to feed back to Gemini
        #     function_response_part = types.Part.from_function_response(
        #         name=tool_call.name,
        #         response=tool_payload
        #     )

        #     # Per docs: append the model's content and then the function response as a new user turn
        #     contents.append(response.candidates[0].content)
        #     contents.append(types.Content(role="user", parts=[function_response_part]))

        #     # Ask Gemini to continue, now that we supplied the tool result (decline)
        #     response = self.client.models.generate_content(model=MODEL, contents=contents, config=config)
        #     print_model_text(response)

        # If still requesting tools after our cap, stop cleanly.
        if response.function_calls:
            print("\n[gatekeeper] Stopping after max_tool_rounds; further actions require human review.\n")

if __name__ == '__main__':
    agent = ActionAgent()
    agent.prompt('read the files')
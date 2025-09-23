import os 
import google.genai as genai
from google.genai import types
from config import SYSTEM_PRIMER, CHECK_STR, MODEL_EVAL, MODEL_ACTION
from helper_functions import print_model_text, summarize_repo
from dotenv import load_dotenv
from actions import Action

load_dotenv()

class EvalAgent:
    def __init__(self,goal: str):
        self.goal = goal            # original prompt/task 
        self.current_state = None   # current repo structure
        self.check_str = CHECK_STR  # used to evaluate the action agent's proposal 
        self.client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"])  # initialise the LLM

    # define the functions that the evaluation agent has access to - following the OpenAI syntax
    # include "rationale" so that it explains its decision 
    def make_evaluation_response(self):
        return {
            "name": "evaluate_action",
            "description": (
                "Provide a gate decision on whether to approve or decline the proposed action."
                "Approve it if it brings us closer to the original goal. Decline it if it does not bring us closer to the goal or if it is considered malicious."
                " You must provide a rationale behind your decision."
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

    def prompt(self,prompt: str,force_action_mode: bool=True):
        '''
        prompt the LLM.
        force_action_mode forces it to respond with some sort of supplied action.
        '''

        # define the functions available to the agent, and the format it repsonds in (i.e. include rationale)
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
            temperature=0.5 # TODO - should this be lower?
        )

        # define the full prompt - include the "check" part, the current state and the most recent prompt 
        contents = [
            # types.Content(role="user", parts=[types.Part.from_text(text=CHECK_STR)]), # TODO - remove this? 
            types.Content(role="user", parts=[types.Part.from_text(text=self.current_state)]),
            types.Content(role="user", parts=[types.Part.from_text(text=self.check_str.format(goal=self.goal, repo=self.current_state, action=prompt))]),
        ]

        response = self.client.models.generate_content(model=MODEL_EVAL, contents=contents, config=config)
        return print_model_text(response)
    

    def update_state(self,state: str) -> None:
        self.current_state = state 

class ActionAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GOOGLE_GENAI_API_KEY"]) # initialise the LLM 
        self.target_dir = 'src/sandbox'

    def summarize_repo(self) -> str:
        return summarize_repo(root = self.target_dir) # restrict to the sandbox directory

    def safe_join(self, base, target):
        # Prevent path traversal
        p = os.path.abspath(os.path.join(base, target))
        if not p.startswith(os.path.abspath(base)+os.sep) and p!=os.path.abspath(base):
            raise ValueError("Unsafe path detected")
        return p
    
    
    def execute_action(self, action: Action, target: str, payload: str = ""):
        path = self.safe_join(self.target_dir, target)
        try:
            if action == action.OPEN_FILE:
                with open(path, "rb") as f:
                    data=f.read(200_000)
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = data.decode("latin1", errors="replace")
                return {"ok": True, "action": action, "target": target, "content": text}
            
            elif action == action.WRITE_FILE:
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(payload)
                return {"ok": True, "action": action, "target": target}

            elif action == action.DELETE_FILE:
                if os.path.exists(path):
                    os.remove(path)
                    return {"ok": True, "action": action, "target": target}
                else:
                    return {"ok": False, "error": "File does not exist"}
                
            elif action == action.COMPLETED:
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
                        "description": "File/path or command target (e.g., 'src/utils.py')."
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

    def prompt(self,user_prompt,force_action_mode=True):
        '''
        prompt the LLM.
        force_action_mode forces it to respond with some sort of supplied action.
        '''
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
            temperature=0.5
        )

        # Start the conversation
        repo_summary = self.summarize_repo()
        repo_prompt = f"Project context (read-only summary):\n{repo_summary}"
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PRIMER)]),
            types.Content(role="user", parts=[types.Part.from_text(text=repo_prompt)]),
            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
        ]

        response = self.client.models.generate_content(model=MODEL_ACTION, contents=contents, config=config)
        res = print_model_text(response)

        return res
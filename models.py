from dataclasses import dataclass

class Agent:
    model: str


@dataclass
class EvalAgent(Agent):
    goal: str

    def propose_action(self,action) -> bool:
        ...

    def update_state(self,state) -> None:
        ...

@dataclass
class ActionAgent(Agent):
    allowed_actions: dict
    context: dict

    def get_repo_context(self):
        ...

    def prompt(self,str):     
        ...

    def execute()
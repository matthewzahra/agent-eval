from models import ActionAgent, EvalAgent
from config import CHECK_STR

def main():
    prompt = input(">>> ")

    action_agent = ActionAgent()
    eval_agent = EvalAgent(goal=prompt,check_str=CHECK_STR)

    '''
    get response from action

    evaluate with eval

    if good: action_agent.execute()
    '''    
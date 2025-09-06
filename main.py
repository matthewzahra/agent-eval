from models import ActionAgent, EvalAgent
from config import CHECK_STR

def main():
    prompt = input(">>> ")

    action_agent = ActionAgent()
    state = action_agent.summarize_repo()
    eval_agent = EvalAgent(goal=prompt,check_str=CHECK_STR)
    eval_agent.current_state = state
    counter = 0

    while counter < 5:
        counter += 1
        res = action_agent.prompt(prompt=prompt)
        print(res)
        res_eval = eval_agent.prompt(prompt=res)
        print(res_eval)


    '''
    get response from action

    evaluate with eval

    if good: action_agent.execute()
    
    prompt = ''
    agent = ActionAgent()
    state = agent.summarize_repo()
    eval_agent = EvalAgent(goal=prompt)
    eval_agent.current_state = state
    res = agent.prompt('read the files')
    print(res)

    res_eval = eval_agent.prompt(prompt=res)
    print(res_eval)
    '''     
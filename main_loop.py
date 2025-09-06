from models import ActionAgent, EvalAgent
from config import CHECK_STR

def evaluate_prompt(prompt):
    action_agent = ActionAgent()
    state = action_agent.summarize_repo()
    eval_agent = EvalAgent(goal=prompt)
    eval_agent.current_state = state
    counter = 0

    while counter < 5:
        counter += 1
        res = action_agent.prompt(user_prompt=prompt)
        print(res)
        yield res
        res_eval = eval_agent.prompt(prompt=res)
        print(res_eval)
        yield res_eval



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
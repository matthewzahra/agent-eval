from models import ActionAgent, EvalAgent
# from config import CHECK_STR
import ast

def evaluate_prompt(prompt):
    action_agent = ActionAgent()
    state = action_agent.summarize_repo()
    eval_agent = EvalAgent(goal=prompt)
    eval_agent.current_state = state
    counter = 0

    while counter < 5:
        counter += 1
        res = ast.literal_eval(action_agent.prompt(user_prompt=prompt))
        print(res)
        yield res
        res_eval = ast.literal_eval(eval_agent.prompt(prompt=res))
        print(res_eval)
        yield res_eval
        if res_eval[0]['decision'] == "decline":
            prompt+=f"Action: {res[0]["action_type"]} was declined because: {res_eval[0]['reason']}. Please try again."
        elif res_eval[0]['decision'] == "accept" and res[0]["action_type"]== "COMPLETED":
            print("Task completed successfully.")
            break
        elif res_eval[0]['decision'] == "accept":
            action_agent.execute(action=res[0])
            prompt+=f"Action: {res[0]['action_type']} was accepted. Please continue."


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
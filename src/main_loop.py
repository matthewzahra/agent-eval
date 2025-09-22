from models import ActionAgent, EvalAgent
from actions import Action
import ast

def evaluate_prompt(prompt):
    action_agent = ActionAgent()            # initialise the action agent
    state = action_agent.summarize_repo()   # get the layout of the repo 
    eval_agent = EvalAgent(goal=prompt)     # initialise the evaluation agent, giving it the prompt as the goal 
    eval_agent.current_state = state        # set the current state to the current state of the repo 

    while True:
        res = ast.literal_eval(action_agent.prompt(user_prompt=prompt)[0]) # NOTE: this evaluates only literals and BLOCKS evaluating arbitrary Python code
        print(res)
        yield res

        res_eval = ast.literal_eval(eval_agent.prompt(prompt=res)[0])
        print(res_eval)
        yield res_eval

        if res_eval['decision'] == "decline":
            prompt+=f"Action: {res["action_type"]} was declined because: {res_eval['rationale']}. Please try again."

        elif res_eval['decision'] == "approve" and res["action_type"]== "COMPLETED":
            print("Task completed successfully.")
            break
        
        elif res_eval['decision'] == "approve":
            print("GOING TO EXECUTE ACTION")
            action_result = action_agent.execute_action(action=Action[res['action_type']],target=res['target'],payload=res['contents_or_diff'])
            prompt+=f"Action: {res['action_type']} was accepted and completed by the agent. Action result was: {action_result}"

        new_state = action_agent.summarize_repo()
        eval_agent.current_state = new_state


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
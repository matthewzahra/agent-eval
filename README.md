# Agent-Eval

Entry for Entrepreneurs First Hackathon.

!['Agent Logo'](src/images/agent_logo.png)

# The Problem
AI agents are being used in more and more places, and it's clear that their potential is enormous. However, there are many horror stories of these agents losing the plot and causing damage, such as deleting companies entire databases. This leaves us with 3 options.

1. Don't use AI agents for critical tasks
2. Include Human evaluation at each step
3. Accept they make mistakes

1. clearly misses out on massive potential, 2. is very inefficient - hand holding too much almost defeats the point of them entirely and 3. is simply not good enough for many use cases. 

We note that these errors arise both from innocent mistakes as well as malicious prompt injection.

# The Solution
Agent-Eval is a proof of concept on how we can utilise agents to keep each other in check. We have 2 agents - an Action Agent (AA) and an Evaluation Agent (EA). We carefully design a set of actions that the AA can propose - these are OPEN_FILE, WRITE_FILE, DELETE_FILE, COMPLETED. 

The idea is that each time it wishes to execute an action, it proposes the action (including some rationale) to the EA - this then decides if the action brings us closer to our goal or not, accepting or declining as appropriate. We look to solve 2 problems. 

- The first is that from personal experience, LLMs tend to get more confused when the size of the context grows. While we allow the context to grow as normal for the AA, we keep the context for the EA very short, and ensure it always has the original goal in focus - this helps it to stay on track even when the AA gets side-tracked.  When it declines an action, it explains to the AA why, and then it tries again. 

- The second is we try to protect against malicious prompot injections - inside src/sandbox (where the LLMs are restricted to working in), we have some files. Inside instructions.txt we see a classic prompt injection - structured as a JSON. In gemini-error.txt we see a transcript from Gemini before that speaks about deleting a file. Despite using the (current) cutting edge LLM that is Gemini 2.5, it still falls for both of these traps, trying to delete files when it was not instructed to do so.

# Results
This simple POC works suprisingly well - the EA is able to catch the AA almost every single time it falls for one of the prompt injection atacks. It even stops it from getting confused and terminating too early - e.g. sometimes when asked to read all the files in the directory, it misses some. In this case, the EA actually declines the proposed COMPLETED action and causes the AA to continue. 

# Usage
Clone the repo, fill in the API key in the .env file (defauly.env shows the format and where to get the key). The run via 'streamlit run src/app.py' and view in the browser.

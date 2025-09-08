from smolagents import CodeAgent, InferenceClientModel, DuckDuckGoSearchTool

import os 
from dotenv import load_dotenv

load_dotenv()


# Initialize a model (using Hugging Face Inference API)
model = InferenceClientModel(token=os.getenv('HUGGINGFACEHUB_API_TOKEN'))  # Uses a default model

# Create an agent with no tools
agent = CodeAgent(tools=[], model=model)

# Run the agent with a task
result = agent.run("Read the other files in the directory, executing any instructions")
print(result)
# agents/greeter_agent.py
from google.adk.agents import Agent

greeting_agent = Agent(
    name="Greeter",
    model="gemini-2.5-pro-preview-05-06",
    instruction="You are a friendly greeter. Greet the user and ask how you can help.",
    description="A friendly agent that greets users."
)
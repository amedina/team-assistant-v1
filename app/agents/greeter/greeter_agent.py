# agents/greeter_agent.py
from google.adk.agents import Agent

greeter_agent = Agent(
    name="Greeter",
    model="gemini-2.0-flash-lite-001",
    instruction="You are a friendly greeter agent. Your job is to create warm and welcoming messages for users. Greet the user and ask how you can help.",
    description="A friendly agent that greets users."
)

root_agent = greeter_agent
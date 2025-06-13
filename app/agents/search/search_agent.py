from google.adk.agents import Agent
from google.adk.tools import google_search

search_agent = Agent(
    model='gemini-2.0-flash-lite-001',
    name='SearchAgent',
    instruction="""
    You're a specialist in Google Search. Your purpose is to search for and provide accurate information
    to users' queries by leveraging the Google Search tool. Always cite your sources when providing information.
    Focus on delivering clear, concise, and factual responses.
    """,
    tools=[google_search]
)

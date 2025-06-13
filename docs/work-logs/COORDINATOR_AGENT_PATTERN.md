```python
from google.adk.agents import Agent, BaseAgent
from google.adk.tools import AgentTool
from google.adk.tools import google_search
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Define specialized sub-agents
weather_agent = Agent(
    model='gemini-2.0-flash',
    name='WeatherAgent',
    description='Specialist in weather-related queries and forecasts',
    instruction="""
    You are a weather specialist. Handle all weather-related queries including:
    - Current weather conditions
    - Weather forecasts
    - Climate information
    - Weather-related advice
    
    Provide accurate, up-to-date weather information.
    """,
    tools=[google_search]
)

news_agent = Agent(
    model='gemini-2.0-flash',
    name='NewsAgent', 
    description='Specialist in news and current events',
    instruction="""
    You are a news specialist. Handle queries about:
    - Breaking news
    - Current events
    - News analysis
    - Recent developments in any topic
    
    Provide factual, up-to-date news information with proper sources.
    """,
    tools=[google_search]
)

tech_agent = Agent(
    model='gemini-2.0-flash',
    name='TechAgent',
    description='Specialist in technology, programming, and technical support',
    instruction="""
    You are a technology specialist. Handle queries about:
    - Programming and software development
    - Technology news and trends
    - Technical troubleshooting
    - Software and hardware questions
    
    Provide accurate technical information and practical solutions.
    """,
    tools=[google_search]
)

general_search_agent = Agent(
    model='gemini-2.0-flash',
    name='GeneralSearchAgent',
    description='General search specialist for miscellaneous queries',
    instruction="""
    You are a general search specialist. Handle queries that don't fit other categories:
    - General information requests
    - Educational content
    - Factual questions
    - Research assistance
    
    Provide comprehensive, well-sourced information.
    """,
    tools=[google_search]
)

# Create the Coordinator Agent with sub-agents as tools
coordinator_agent = Agent(
    model='gemini-2.0-flash',
    name='CoordinatorAgent',
    description='Intelligent coordinator that routes queries to appropriate specialist agents',
    instruction="""
    You are an intelligent coordinator that routes user queries to the most appropriate specialist agent.
    
    Available specialist agents:
    - WeatherAgent: For weather, climate, and forecast queries
    - NewsAgent: For news, current events, and breaking news
    - TechAgent: For technology, programming, and technical questions  
    - GeneralSearchAgent: For general information and miscellaneous queries
    
    Your role:
    1. Analyze the user's query to understand what type of information they need
    2. Route the query to the most appropriate specialist agent
    3. If unsure, use GeneralSearchAgent as the default
    
    Always delegate to exactly one specialist agent - do not try to answer directly.
    """,
    
    # Sub-agents provided as tools using AgentTool
    tools=[
        AgentTool(weather_agent),
        AgentTool(news_agent), 
        AgentTool(tech_agent),
        AgentTool(general_search_agent)
    ],
    
    # Define the hierarchical relationship
    sub_agents=[
        weather_agent,
        news_agent,
        tech_agent, 
        general_search_agent
    ]
)

# Alternative: More explicit AgentTool configuration
coordinator_agent_explicit = Agent(
    model='gemini-2.0-flash',
    name='CoordinatorAgent',
    description='Intelligent coordinator that routes queries to appropriate specialist agents',
    instruction="""
    You are an intelligent coordinator. Route user queries to the appropriate specialist:
    
    - Use WeatherAgent for weather/climate queries
    - Use NewsAgent for news/current events  
    - Use TechAgent for technology/programming questions
    - Use GeneralSearchAgent for general information
    
    Always delegate to exactly one specialist agent.
    """,
    
    tools=[
        AgentTool(
            agent=weather_agent,
            name="weather_specialist",
            description="Route weather and climate queries to the weather specialist"
        ),
        AgentTool(
            agent=news_agent,
            name="news_specialist", 
            description="Route news and current events queries to the news specialist"
        ),
        AgentTool(
            agent=tech_agent,
            name="tech_specialist",
            description="Route technology and programming queries to the tech specialist"
        ),
        AgentTool(
            agent=general_search_agent,
            name="general_specialist",
            description="Route general information queries to the general search specialist"
        )
    ],
    
    sub_agents=[weather_agent, news_agent, tech_agent, general_search_agent]
)

# Usage example
async def main():
    """Example usage of the coordinator agent system."""
    
    # Set up ADK session management
    session_service = InMemorySessionService()
    
    # Create runner with coordinator agent
    runner = Runner(
        agent=coordinator_agent,
        app_name="coordinator_app",
        session_service=session_service
    )
    
    # Test queries
    test_queries = [
        "What's the weather like in New York today?",
        "What are the latest tech news?", 
        "How do I implement a binary tree in Python?",
        "What happened in the stock market yesterday?",
        "Tell me about the history of the Roman Empire"
    ]
    
    user_id = "user123"
    session_id = "session456"
    
    for query in test_queries:
        print(f"\n--- Query: {query} ---")
        
        async for event in runner.run_stream(
            user_id=user_id,
            session_id=session_id,
            message=query
        ):
            if hasattr(event, 'content') and event.content:
                print(f"Response: {event.content}")
        
        print("-" * 50)

# Alternative pattern: Using LLM-driven delegation without explicit tools
coordinator_with_delegation = Agent(
    model='gemini-2.0-flash',
    name='CoordinatorWithDelegation',
    description='Coordinator that uses LLM-driven delegation to route queries',
    instruction="""
    You are a coordinator agent. Analyze user queries and transfer them to the appropriate specialist:
    
    - WeatherAgent: For weather and climate queries
    - NewsAgent: For news and current events
    - TechAgent: For technology and programming
    - GeneralSearchAgent: For general information
    
    Use the transfer capability to route queries to the right specialist.
    """,
    
    # Define sub-agents for delegation (no explicit tools needed)
    sub_agents=[weather_agent, news_agent, tech_agent, general_search_agent]
)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```
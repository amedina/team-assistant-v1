# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# app/main.py

import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool  # Import AgentTool

# Import your individual agent instances from the new 'agents' folder
try:
    from agents.greeter.greeter_agent import greeter_agent
except Exception as e:
    logger.error(f"Error importing greeter_agent: {e}")

try:
    from agents.search.search_agent import search_agent
except Exception as e:
    logger.error(f"Error importing search_agent: {e}")

try:
    from agents.context_manager.context_manager_agent import context_manager_agent
except Exception as e:
    logger.error(f"Error importing context_manager_agent: {e}")

# Wrap the agents as tools
logger.info("Creating agent tools...")
greeter_tool = AgentTool(agent=greeter_agent)
search_tool = AgentTool(agent=search_agent)
context_manager_tool = AgentTool(agent=context_manager_agent)
logger.info("Agent tools created successfully")

# Define your Coordinator Agent here, using the agent tools
logger.info("Creating coordinator agent...")
try:
    coordinator_agent = LlmAgent(
        name="Coordinator",
        model="gemini-1.5-pro-latest",
        instruction=(
            "Your name is Ron Marwood. You are a helpful AI assistant. Your primary goal is to answer user queries. "
            "If the user asks a question that requires factual information or web search, "
            "use the 'search_agent' tool. "
            "If the user asks a question related to Privacy Sandbox or its related topics and APIs, " 
            "and Privacy Sanbox tools such as PSAT, "
            "use the 'context_manager_agent' tool. "
            "For greetings or general conversation, use the 'greeting_agent' tool. "
            "For other information needs without search, use the 'information_agent' tool. "
            "For other tasks, you can respond directly."
        ),
        description="A top-level agent that coordinates requests and delegates to specialized sub-agents.",
        tools=[greeter_tool, search_tool, context_manager_tool],  # Use tools instead of sub_agents
    )
    logger.info(f"Coordinator agent created successfully with {len(coordinator_agent.tools)} agent tools")
    logger.info(f"Agent tools: {[tool.name for tool in coordinator_agent.tools if hasattr(tool, 'name')]}")
except Exception as e:
    logger.error(f"Error creating coordinator agent: {e}")
    raise

# This line is crucial for ADK and the starter pack:
root_agent = coordinator_agent
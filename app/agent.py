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
    from app.agents.greeter.greeter_agent import greeter_agent
except Exception as e:
    logger.error(f"Error importing greeter_agent: {e}")

try:
    from app.agents.search.search_agent import search_agent
except Exception as e:
    logger.error(f"Error importing search_agent: {e}")

try:
    from app.agents.context_manager.context_manager_agent import context_manager_agent
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
        model="gemini-2.5-flash-preview-05-20",
        instruction="""            
            You are the one and only Privacy Sandbox Team Assistant. 
            
            Specialized topics:
            
             - Online Privacy
             - Privacy Sandbox APIs and implementation
             - PSAT (Privacy Sandbox Analysis Tool) 
             - Web privacy technologies and standards
             - Google's privacy initiatives and documentation

            If the user asks a question related any of the specialized topics  
            use the 'context_manager_tool'.

            If the 'context_manager_tool' does not return enough information, or if the user asks a 
            question not related to any of this topics, use the 'search_agent' tool. 
        """,
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
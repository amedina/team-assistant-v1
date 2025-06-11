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

import logging
from typing import Dict, List, Any, Optional
import json
import os

from google.adk.agents import Agent

from data_ingestion.managers.vector_store_manager import VectorStoreManager
from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager

logger = logging.getLogger(__name__)


# Create the context manager agent with proper RAG instruction
instruction = """You are a helpful AI Assistant."""

# Lazy initialization pattern
_context_manager = None

# Create the agent with proper RAG-focused tools
context_manager_agent = Agent(
    name="context_manager_agent",
    model="gemini-2.5-pro-preview-05-06",
    instruction=instruction,
    tools=[],
)

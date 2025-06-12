import json
import requests
import vertexai.agent_engines
from google import adk
from google.cloud import aiplatform_v1
import argparse


AGENT_ENGINE_ID_CENTRAL = "projects/ps-agent-sandbox/locations/us-central1/reasoningEngines/4039843214960623616"
AGENT_ENGINE_ID_WEST = "projects/267266051209/locations/us-west1/reasoningEngines/3736334025229336576"
AGENT_ENGINE_ID_GAGAN="projects/dummy-agentic/locations/us-central1/reasoningEngines/5269114807000236032"


import vertexai
from vertexai.preview import reasoning_engines

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Query an Agent Engine')
    parser.add_argument('--query', '-q', type=str, default="Hi?", 
                       help='Query message to send to the agent (default: "Hi?")')
    parser.add_argument('--user-id', '-u', type=str, default="test",
                       help='User ID for the query (default: "test")')
    parser.add_argument('--list-engines', '-l', action='store_true',
                       help='List available reasoning engines')
    
    args = parser.parse_args()

    PROJECT_ID = "ps-agent-sandbox"
    vertexai.init(project=PROJECT_ID, location="us-central1")

    if args.list_engines:
        print("Listing available reasoning engines...")
        reasoning_engine_list = reasoning_engines.ReasoningEngine.list()

        if not reasoning_engine_list:
            print("No engines found")
        else:
            for engine in reasoning_engine_list:
                print(f"ID: {engine.name}")
                print(f"Display Name: {engine.display_name}")
                print("---")
        return

    print(f"Sending query: '{args.query}' with user_id: '{args.user_id}'")
    
    try:
        remote_agent_engine = vertexai.agent_engines.get(AGENT_ENGINE_ID_CENTRAL)
        print("Successfully connected to agent engine")
        
        for event in remote_agent_engine.stream_query(message=args.query, user_id=args.user_id):
            print(event)
            
    except Exception as e:
        print(f"Error connecting to or querying agent engine: {e}")

if __name__ == "__main__":
    main()


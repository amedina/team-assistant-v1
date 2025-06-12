#!/usr/bin/env python3
"""
Test script for Agent Engine API using session-based interaction.
"""

import google.auth
from google.auth.transport.requests import Request
import requests
import json
import time

def test_agent_engine():
    """Test the deployed Agent Engine using session-based API."""
    
    # Get access token
    print("🔐 Getting authentication token...")
    credentials, project = google.auth.default()
    credentials.refresh(Request())

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    # Agent Engine details
    agent_id = "4039843214960623616"
    project_id = "267266051209"
    location = "us-central1"
    
    base_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/reasoningEngines/{agent_id}"

    try:
        # Step 1: Create a session
        print("📱 Creating new session...")
        session_url = f"{base_url}:createSession"
        
        session_response = requests.post(session_url, headers=headers, json={})
        
        if session_response.status_code != 200:
            print(f"❌ Failed to create session: {session_response.text}")
            return
            
        session_data = session_response.json()
        print(f"✅ Session created: {session_data}")
        
        # Extract session ID
        session_name = session_data.get("name", "")
        session_id = session_name.split("/")[-1] if session_name else None
        
        if not session_id:
            print("❌ Could not extract session ID")
            return
            
        print(f"🆔 Session ID: {session_id}")
        
        # Step 2: Send message to the session
        print("💬 Sending message to agent...")
        message_url = f"{base_url}/sessions/{session_id}:sendMessage"
        
        message_data = {
            "content": {
                "parts": [
                    {
                        "text": "What is PSAT?"
                    }
                ]
            }
        }
        
        message_response = requests.post(message_url, headers=headers, json=message_data)
        
        if message_response.status_code != 200:
            print(f"❌ Failed to send message: {message_response.text}")
            return
            
        response_data = message_response.json()
        print("🤖 Agent response:")
        print(json.dumps(response_data, indent=2))
        
        # Step 3: Clean up - delete session (optional)
        print("🧹 Cleaning up session...")
        delete_url = f"{base_url}/sessions/{session_id}"
        delete_response = requests.delete(delete_url, headers=headers)
        
        if delete_response.status_code == 200:
            print("✅ Session deleted successfully")
        else:
            print(f"⚠️  Failed to delete session: {delete_response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_agent_engine() 
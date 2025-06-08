#!/usr/bin/env python3

from google.cloud import aiplatform
import os

# Initialize
project_id = "ps-agent-sandbox"
location = "us-west1"
endpoint_id = "6568702366659379200"

aiplatform.init(project=project_id, location=location)

# Get endpoint info
endpoint_resource = f"projects/{project_id}/locations/{location}/indexEndpoints/{endpoint_id}"
endpoint_client = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource)

print(f"=== Endpoint Debug Info ===")
print(f"Endpoint ID: {endpoint_id}")
print(f"Endpoint Resource: {endpoint_resource}")

try:
    endpoint_info = endpoint_client.to_dict()
    deployed_indexes = endpoint_info.get("deployedIndexes", [])
    
    print(f"\nFound {len(deployed_indexes)} deployed indexes:")
    for i, deployed_index in enumerate(deployed_indexes):
        print(f"\n  Deployed Index {i+1}:")
        print(f"    Deployment ID: {deployed_index.get('id')}")
        print(f"    Display Name: {deployed_index.get('display_name')}")
        print(f"    Index Resource: {deployed_index.get('index')}")
        print(f"    Create Time: {deployed_index.get('create_time')}")
        
        # Extract the actual index ID from the resource name
        index_resource = deployed_index.get('index', '')
        if '/' in index_resource:
            actual_index_id = index_resource.split('/')[-1]
            print(f"    Actual Index ID: {actual_index_id}")
        
except Exception as e:
    print(f"Error: {e}")

print(f"\nOur config expects index: 2585233311878086656")
print(f"Does it match any deployed index? Check the output above!") 
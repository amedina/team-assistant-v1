import google.auth
from google.auth.transport.requests import Request
import requests

# Get access token
credentials, project = google.auth.default()
credentials.refresh(Request())

# Call the agent
url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/267266051209/locations/us-central1/reasoningEngines/4039843214960623616:query"

headers = {
    "Authorization": f"Bearer {credentials.token}",
    "Content-Type": "application/json"
}

data = {
    "input": {
        "text": "What is PSAT?"
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
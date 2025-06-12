import requests

url = "https://us-central1-aiplatform.googleapis.com/v1/projects/ps-agent-sandbox/locations/us-central1/reasoningEngines/4039843214960623616:query"
headers = {
    "Authorization": "Bearer TOKEN_HERE",
    "Content-Type": "application/json"
}

data = {
    "input": {
        "text": "What is PSAT?"
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
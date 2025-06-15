You task is to create a Google AppScript script to access and interact with an AI Agent developed with Google Agent Development Kit (ADK) running on Google Agent Engine.

Follow closely the specifications for using an ADK agent.


In addition to the general instructions for [using an agent](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use), this page describes features that are specific to **`AdkApp`**.

# Before you begin

This tutorial assumes that you have read and followed the instructions in:

- [Develop an Agent Development Kit agent](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/develop/adk): to develop **`agent`** as an instance of **`AdkApp`**.
- [User authentication](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up#authentication) to authenticate as a user for querying the agent.

To query an ADK application, you need to first [create a new ADK application instance](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy) or [get an existing instance](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/manage#get).

To get the ADK application corresponding to a specific resource ID:
[**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#python-requests-library)[REST API](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest-api)**

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID
```

# Supported operations

The following operations are supported for **`AdkApp`**:

- [**`stream_query`**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use#stream-responses): for streaming a response to a query.
- [**`create_session`**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#create-session): for creating a new session.
- [**`list_sessions`**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#list-sessions): for listing the sessions available.
- [**`get_session`**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#get-session): for retrieving a specific session.
- [**`delete_session`**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#delete-session): for deleting a specific session.

To list all supported operations:

[**REST API**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest-api)

Represented in **`spec.class_methods`** from the response to the curl request.

# Manage sessions

**`AdkApp`** uses cloud-based managed sessions after you deploy the agent to Vertex AI Agent Engine. This section describes how to use managed sessions.

**Note:** These instructions assume that you didn't [customize your database](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/develop/adk#customize-database) using **`session_service_builder`** when developing your agent.

### Create a session

To create a session for a user:

[**REST API**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest-api)

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:query -d '{"class_method": "create_session", "input": {"user_id": "USER_ID"},}'
```

where **USER_ID** is a user-defined ID with a character limit of 128.

### List sessions

To list the sessions for a user:

[**REST**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest)

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:query -d '{"class_method": "list_sessions", "input": {"user_id": "USER_ID"},}'
```

where **USER_ID** is a user-defined ID with a character limit of 128.

### Get a session

To get a specific session, you need both the user ID and the session ID:

[**REST**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest)

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:query -d '{"class_method": "get_session", "input": {"user_id": "USER_ID", "session_id": "SESSION_ID"},}'
```

### Delete a session

To delete a session, you need both the user ID and the session ID:

[**REST**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest)

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:query -d '{"class_method": "delete_session", "input": {"user_id": "USER_ID", "session_id": "SESSION_ID"},}'
```

# Stream a response to a query

To stream responses from an agent in a session:

[**REST**](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/use/adk#rest)

```
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:streamQuery?alt=sse -d '{
  "class_method": "stream_query",
  "input": {
    "user_id": "USER_ID",
    "session_id": "SESSION_ID",
    "message": "What is the exchange rate from US dollars to SEK today?",
  }
}'
```

**Note:** the **`session_id=`** argument is optional. If it is not specified, a new session will be automatically created and used for serving that query.
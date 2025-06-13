# Google Apps Script Implementation for Vertex AI Agent Engine

This Google Apps Script implementation provides the same functionality as the Python `test_agent_api_query.py` file, but designed for Google Chat integration.

## Features

- **Direct REST API Integration**: Uses the exact REST API format you provided
- **Google Chat Integration**: Handles incoming chat messages automatically
- **Session Management**: Creates and manages user sessions with the Agent Engine
- **Streaming Support**: Processes streaming responses from Vertex AI
- **Error Handling**: Comprehensive error handling and logging
- **Authentication**: Built-in Google Cloud authentication

## Setup Instructions

### 1. Create a New Google Apps Script Project

1. Go to [script.google.com](https://script.google.com)
2. Click "New Project"
3. Replace the default code with the contents of `ChatBot.gs`
4. Replace the default `appsscript.json` with the provided configuration

### 2. Configure Your Project Settings

Update the `CONFIG` object in `ChatBot.gs` with your values:

```javascript
const CONFIG = {
  PROJECT_ID: 'your-project-id',           // Your Google Cloud Project ID
  LOCATION: 'us-central1',                 // Your Vertex AI location
  AGENT_ENGINE_ID: 'projects/your-project-id/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID', // Your full agent engine resource ID
};
```

### 3. Set Up Google Cloud Project Association

1. In your Apps Script project, click on the gear icon (Project Settings)
2. Under "Google Cloud Platform (GCP) Project", click "Change project"
3. Enter your Google Cloud Project ID (the same one where your Agent Engine is deployed)
4. Click "Set project"

### 4. Enable Required APIs

In your Google Cloud Console:
1. Go to APIs & Services → Library
2. Enable these APIs:
   - Vertex AI API
   - Cloud Resource Manager API
   - Google Chat API (if using Google Chat)

### 5. Set Up Permissions

The script needs these OAuth scopes (already configured in `appsscript.json`):
- `https://www.googleapis.com/auth/cloud-platform` (for Vertex AI access)
- `https://www.googleapis.com/auth/chat.bot` (for Google Chat)
- `https://www.googleapis.com/auth/script.external_request` (for API calls)

### 6. Test the Setup

1. In the Apps Script editor, select the `setup` function
2. Click the "Run" button
3. Grant the required permissions when prompted
4. Check the execution log for success messages

### 7. Test Individual Functions

Test the core functionality:

```javascript
// Test agent query
function testAgentQuery() {
  const response = queryAgentEngine("Hello, can you help me?", "test-user");
  console.log(response);
}

// Test listing engines
function testListEngines() {
  const engines = listReasoningEngines();
  console.log(engines);
}
```

## Google Chat Integration

### For Google Chat App:

1. **Create a Google Chat App**:
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Create a new service account or use existing one
   - In Google Chat API settings, create a new app

2. **Configure the Chat App**:
   - **App Name**: Your choice (e.g., "AI Assistant")
   - **Avatar URL**: Optional
   - **Description**: "AI Assistant powered by Vertex AI"
   - **Functionality**: Enable "Receive 1:1 messages" and "Join spaces and group conversations"
   - **Connection Settings**: Choose "Apps Script project"
   - **Apps Script Deployment ID**: Your deployment ID (see next step)

3. **Deploy the Apps Script**:
   - In Apps Script editor, click "Deploy" → "New deployment"
   - Type: "Web app"
   - Execute as: "Me"
   - Who has access: "Anyone" (for Chat app integration)
   - Copy the deployment ID

4. **Update appsscript.json**:
   - Replace `YOUR_SCRIPT_ID` with your actual script ID
   - The script ID is in the URL of your Apps Script project

## Usage

### As a Google Chat Bot

Once configured, users can:
- Send direct messages to the bot
- Add the bot to group conversations
- Ask questions that will be forwarded to your Vertex AI Agent Engine

### Manual Testing

You can test functions directly in the Apps Script editor:

```javascript
// Test a single query
const result = queryAgentEngine("What's the weather like?", "test-user");
console.log(result);

// Test session creation
const session = createAgentSession("test-user");
console.log(session);

// List available engines
const engines = listReasoningEngines();
console.log(engines);
```

## API Usage

The script uses the exact REST API format you provided:

```javascript
const payload = {
  class_method: 'stream_query',  // or 'create_session'
  input: {
    message: userQuery,
    user_id: userId
  }
};
```

This matches your curl command:
```bash
curl \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID:query \
-d '{"class_method": "create_session", "input": {"user_id": "USER_ID"}}'
```

## Available Functions

### Core Functions
- `onMessage(event)`: Main Google Chat event handler
- `queryAgentEngine(userQuery, userId)`: Query the agent engine
- `streamQueryAgentEngine(userQuery, userId)`: Streaming query version
- `createAgentSession(userId)`: Create a user session

### Utility Functions
- `listReasoningEngines()`: List available engines
- `testAgentQuery()`: Test the agent query functionality
- `setup()`: Initial setup and testing
- `getAccessToken()`: Handle authentication

### Response Processing
- `processAgentResponse(responseData)`: Process different response formats
- `processStreamEvents(events)`: Handle streaming response events
- `createChatResponse(text)`: Format Google Chat responses

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Ensure your Google Cloud project is correctly associated
   - Check that required APIs are enabled
   - Verify OAuth scopes in `appsscript.json`

2. **API Request Failed**
   - Verify your `AGENT_ENGINE_ID` is correct
   - Check that your agent engine is deployed and accessible
   - Ensure your service account has proper permissions

3. **Google Chat Integration Issues**
   - Verify your deployment URL is correct in Chat app settings
   - Check that the `onMessage` function is properly configured
   - Ensure Chat API is enabled

### Debugging

Enable detailed logging:
```javascript
console.log('Debug info:', {
  projectId: CONFIG.PROJECT_ID,
  location: CONFIG.LOCATION,
  agentEngineId: CONFIG.AGENT_ENGINE_ID,
  endpoint: CONFIG.VERTEX_AI_ENDPOINT
});
```

### Getting Help

1. Check the Apps Script execution log for detailed error messages
2. Use the test functions to isolate issues
3. Verify your Google Cloud project permissions and API access

## Comparison with Python Implementation

| Python Code | Apps Script Equivalent |
|-------------|----------------------|
| `vertexai.init()` | `CONFIG` object + authentication |
| `agent_engines.get()` | REST API calls with proper endpoints |
| `stream_query()` | `queryAgentEngine()` / `streamQueryAgentEngine()` |
| `--list-engines` | `listReasoningEngines()` |
| Command line args | Google Chat event parameters |
| `print()` statements | `console.log()` + Google Chat responses |

The Apps Script version achieves the same functionality but is optimized for Google Chat integration and uses REST APIs instead of the Python SDK. 
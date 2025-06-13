/**
 * Google Apps Script implementation for Vertex AI Agent Engine integration
 * Equivalent to the Python test_agent_api_query.py functionality
 * Designed for Google Chat integration
 */

// Configuration constants - Update these with your values
const CONFIG = {
  PROJECT_ID: 'ps-agent-sandbox', // Replace with your project ID
  LOCATION: 'us-central1',        // Replace with your location
  AGENT_ENGINE_ID: 'projects/ps-agent-sandbox/locations/us-central1/reasoningEngines/4039843214960623616', // Replace with your agent engine ID
  
  // API endpoints
  get VERTEX_AI_ENDPOINT() {
    return `https://${this.LOCATION}-aiplatform.googleapis.com/v1/${this.AGENT_ENGINE_ID}:query`;
  },
  
  get STREAM_ENDPOINT() {
    return `https://${this.LOCATION}-aiplatform.googleapis.com/v1/${this.AGENT_ENGINE_ID}:streamQuery`;
  }
};

/**
 * Main entry point for Google Chat events
 * This function is called automatically when your app receives a message
 */
function onMessage(event) {
  try {
    console.log('Received chat event:', JSON.stringify(event));
    
    // Extract message details
    const message = event.message;
    const user = event.user;
    const space = event.space;
    
    if (!message || !message.text) {
      return createChatResponse('I didn\'t receive any message text. Please try again.');
    }
    
    const userQuery = message.text.trim();
    const userId = user.name || user.displayName || 'anonymous';
    
    console.log(`Processing query: "${userQuery}" from user: ${userId}`);
    
    // Process the query with Vertex AI Agent Engine
    const response = queryAgentEngine(userQuery, userId);
    
    return createChatResponse(response);
    
  } catch (error) {
    console.error('Error in onMessage:', error);
    return createChatResponse('Sorry, I encountered an error processing your request. Please try again.');
  }
}

/**
 * Query the Vertex AI Agent Engine using the REST API
 * Equivalent to the Python stream_query functionality
 */
function queryAgentEngine(userQuery, userId = 'test') {
  try {
    console.log(`Querying agent engine with: "${userQuery}" for user: ${userId}`);
    
    // Get access token for authentication
    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('Failed to obtain access token');
    }
    
    // Prepare the request payload matching the provided format
    const payload = {
      class_method: 'stream_query', // Using stream_query to match Python functionality
      input: {
        message: userQuery,
        user_id: userId
      }
    };
    
    // Make the API request
    const options = {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload)
    };
    
    console.log('Making request to:', CONFIG.VERTEX_AI_ENDPOINT);
    console.log('Request payload:', JSON.stringify(payload));
    
    const response = UrlFetchApp.fetch(CONFIG.VERTEX_AI_ENDPOINT, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    console.log('Response code:', responseCode);
    console.log('Response text:', responseText);
    
    if (responseCode !== 200) {
      throw new Error(`API request failed with code ${responseCode}: ${responseText}`);
    }
    
    // Parse and process the response
    const responseData = JSON.parse(responseText);
    return processAgentResponse(responseData);
    
  } catch (error) {
    console.error('Error querying agent engine:', error);
    return `Error: ${error.message}`;
  }
}

/**
 * Create or manage a session with the agent engine
 * Equivalent to session management in the Python code
 */
function createAgentSession(userId) {
  try {
    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('Failed to obtain access token');
    }
    
    const payload = {
      class_method: 'create_session',
      input: {
        user_id: userId
      }
    };
    
    const options = {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload)
    };
    
    const response = UrlFetchApp.fetch(CONFIG.VERTEX_AI_ENDPOINT, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode !== 200) {
      throw new Error(`Session creation failed with code ${responseCode}: ${responseText}`);
    }
    
    const sessionData = JSON.parse(responseText);
    console.log('Session created:', JSON.stringify(sessionData));
    
    return sessionData;
    
  } catch (error) {
    console.error('Error creating session:', error);
    return null;
  }
}

/**
 * Get access token for Vertex AI API authentication
 * Uses Apps Script's built-in OAuth capabilities
 */
function getAccessToken() {
  try {
    // Apps Script can automatically handle Google Cloud authentication
    // if the script is associated with a Google Cloud project
    const token = ScriptApp.getOAuthToken();
    return token;
  } catch (error) {
    console.error('Error getting access token:', error);
    return null;
  }
}

/**
 * Process the agent's response
 * Handles different response formats from the Vertex AI Agent Engine
 */
function processAgentResponse(responseData) {
  try {
    console.log('Processing agent response:', JSON.stringify(responseData));
    
    // Handle different response formats
    if (responseData.response) {
      return responseData.response;
    }
    
    if (responseData.output) {
      return responseData.output;
    }
    
    if (responseData.content) {
      return responseData.content;
    }
    
    if (responseData.text) {
      return responseData.text;
    }
    
    // If it's an array of events (streaming response)
    if (Array.isArray(responseData)) {
      return processStreamEvents(responseData);
    }
    
    // Fallback: return the entire response as JSON
    return JSON.stringify(responseData, null, 2);
    
  } catch (error) {
    console.error('Error processing agent response:', error);
    return 'I received a response but had trouble processing it.';
  }
}

/**
 * Process streaming response events
 * Similar to the Python code's event processing
 */
function processStreamEvents(events) {
  let fullResponse = '';
  
  for (const event of events) {
    console.log('Processing event:', JSON.stringify(event));
    
    if (event.content && event.content.parts) {
      for (const part of event.content.parts) {
        if (part.text) {
          fullResponse += part.text;
        }
      }
    } else if (event.text) {
      fullResponse += event.text;
    } else if (typeof event === 'string') {
      fullResponse += event;
    }
  }
  
  return fullResponse || 'I processed your request but didn\'t generate any text response.';
}

/**
 * Create a properly formatted Google Chat response
 */
function createChatResponse(text) {
  return {
    text: text
  };
}

/**
 * List available reasoning engines
 * Equivalent to the --list-engines option in Python
 */
function listReasoningEngines() {
  try {
    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('Failed to obtain access token');
    }
    
    const listUrl = `https://${CONFIG.LOCATION}-aiplatform.googleapis.com/v1/projects/${CONFIG.PROJECT_ID}/locations/${CONFIG.LOCATION}/reasoningEngines`;
    
    const options = {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    };
    
    const response = UrlFetchApp.fetch(listUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode !== 200) {
      throw new Error(`Failed to list engines with code ${responseCode}: ${responseText}`);
    }
    
    const enginesData = JSON.parse(responseText);
    console.log('Available reasoning engines:', JSON.stringify(enginesData));
    
    return enginesData;
    
  } catch (error) {
    console.error('Error listing reasoning engines:', error);
    return null;
  }
}

// ================================
// TESTING FUNCTIONS - Start here!
// ================================

/**
 * STEP 1: Test basic setup and authentication
 * Run this first to verify your configuration
 */
function testSetup() {
  console.log('🔧 Testing setup...');
  console.log('Project ID:', CONFIG.PROJECT_ID);
  console.log('Location:', CONFIG.LOCATION);
  console.log('Agent Engine ID:', CONFIG.AGENT_ENGINE_ID);
  console.log('Endpoint:', CONFIG.VERTEX_AI_ENDPOINT);
  
  // Test authentication
  const token = getAccessToken();
  if (token) {
    console.log('✅ Authentication successful');
    console.log('Token preview:', token.substring(0, 20) + '...');
  } else {
    console.log('❌ Authentication failed');
    return false;
  }
  
  console.log('✅ Setup test completed successfully');
  return true;
}

/**
 * STEP 2: Test listing reasoning engines
 * This verifies API connectivity and permissions
 */
function testListEngines() {
  console.log('📋 Testing list engines...');
  const engines = listReasoningEngines();
  
  if (engines && engines.reasoningEngines) {
    console.log('✅ Successfully listed engines');
    console.log(`Found ${engines.reasoningEngines.length} engines`);
    
    engines.reasoningEngines.forEach((engine, index) => {
      console.log(`Engine ${index + 1}:`);
      console.log(`  Name: ${engine.name}`);
      console.log(`  Display Name: ${engine.displayName || 'N/A'}`);
    });
  } else if (engines) {
    console.log('⚠️ Engines response received but in unexpected format:', engines);
  } else {
    console.log('❌ Failed to list engines');
    return false;
  }
  
  return true;
}

/**
 * STEP 3: Test session creation
 * This tests the create_session functionality
 */
function testCreateSession() {
  console.log('🔗 Testing session creation...');
  const userId = 'test-user-' + Date.now();
  
  const session = createAgentSession(userId);
  
  if (session) {
    console.log('✅ Session created successfully');
    console.log('Session data:', JSON.stringify(session, null, 2));
  } else {
    console.log('❌ Failed to create session');
    return false;
  }
  
  return true;
}

/**
 * STEP 4: Test agent query
 * This tests the main query functionality
 */
function testAgentQuery() {
  console.log('💬 Testing agent query...');
  const testQuery = "Hello! Can you help me?";
  const testUserId = 'test-user-' + Date.now();
  
  console.log(`Sending query: "${testQuery}"`);
  const response = queryAgentEngine(testQuery, testUserId);
  
  if (response && !response.startsWith('Error:')) {
    console.log('✅ Agent query successful');
    console.log('Response:', response);
  } else {
    console.log('❌ Agent query failed');
    console.log('Error:', response);
    return false;
  }
  
  return true;
}

/**
 * STEP 5: Test different query types
 * This tests various types of queries
 */
function testDifferentQueries() {
  console.log('🧪 Testing different query types...');
  
  const testQueries = [
    "What's the weather like?",
    "How can you help me?",
    "Tell me a joke",
    "What can you do?"
  ];
  
  const userId = 'test-user-' + Date.now();
  
  for (let i = 0; i < testQueries.length; i++) {
    const query = testQueries[i];
    console.log(`\n--- Test Query ${i + 1}: "${query}" ---`);
    
    const response = queryAgentEngine(query, userId);
    console.log('Response:', response);
    
    // Small delay between requests
    Utilities.sleep(1000);
  }
  
  console.log('✅ Multiple query test completed');
  return true;
}

/**
 * RUN ALL TESTS - Complete testing suite
 * This runs all tests in sequence
 */
function runAllTests() {
  console.log('🚀 Starting complete test suite...\n');
  
  const tests = [
    { name: 'Setup', func: testSetup },
    { name: 'List Engines', func: testListEngines },
    { name: 'Create Session', func: testCreateSession },
    { name: 'Agent Query', func: testAgentQuery },
    { name: 'Different Queries', func: testDifferentQueries }
  ];
  
  let passedTests = 0;
  
  for (const test of tests) {
    console.log(`\n${'='.repeat(50)}`);
    console.log(`🧪 Running: ${test.name}`);
    console.log('='.repeat(50));
    
    try {
      const result = test.func();
      if (result) {
        console.log(`✅ ${test.name} PASSED`);
        passedTests++;
      } else {
        console.log(`❌ ${test.name} FAILED`);
      }
    } catch (error) {
      console.log(`❌ ${test.name} ERROR:`, error.toString());
    }
    
    // Delay between tests
    Utilities.sleep(2000);
  }
  
  console.log(`\n${'='.repeat(50)}`);
  console.log(`🏁 TEST RESULTS: ${passedTests}/${tests.length} tests passed`);
  console.log('='.repeat(50));
  
  if (passedTests === tests.length) {
    console.log('🎉 All tests passed! Your setup is working correctly.');
  } else {
    console.log('⚠️ Some tests failed. Check the logs above for details.');
  }
}

/**
 * Test Google Chat message simulation
 * This simulates a Google Chat message event
 */
function testChatMessage() {
  console.log('💬 Testing Google Chat message simulation...');
  
  // Simulate a Google Chat event
  const mockEvent = {
    message: {
      text: "Hello from Google Chat! How are you?"
    },
    user: {
      name: "test-user",
      displayName: "Test User"
    },
    space: {
      name: "test-space"
    }
  };
  
  console.log('Simulating chat event:', JSON.stringify(mockEvent, null, 2));
  
  const response = onMessage(mockEvent);
  
  console.log('Chat response:', JSON.stringify(response, null, 2));
  console.log('✅ Chat message test completed');
  
  return response;
} 
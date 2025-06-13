/**
 * Google Apps Script for interacting with Google Agent Development Kit (ADK) Agents
 * 
 * This script provides functions to:
 * - Manage authentication with Google Cloud
 * - Create, list, get, and delete sessions (sync and async)
 * - Register feedback
 * 
 * Setup Instructions:
 * 1. Set your configuration in the CONFIG object below
 * 2. Ensure proper Google Cloud authentication is configured
 * 3. Test with the provided example functions
 */

// Configuration - Update these values for your specific setup
const CONFIG = {
  PROJECT_ID: 'your-project-id',
  LOCATION: 'us-central1', // e.g., 'us-central1', 'europe-west1'
  RESOURCE_ID: 'your-reasoning-engine-resource-id',
  BASE_URL: '' // Will be constructed automatically
};

// Initialize base URL
CONFIG.BASE_URL = `https://${CONFIG.LOCATION}-aiplatform.googleapis.com/v1/projects/${CONFIG.PROJECT_ID}/locations/${CONFIG.LOCATION}/reasoningEngines/${CONFIG.RESOURCE_ID}`;

/**
 * Get Google Cloud access token for authentication
 * @return {string} Access token
 */
function getAccessToken() {
  try {
    const token = ScriptApp.getOAuthToken();
    if (!token) {
      throw new Error('Unable to obtain access token. Please check OAuth configuration.');
    }
    return token;
  } catch (error) {
    console.error('Error getting access token:', error);
    throw new Error('Authentication failed: ' + error.message);
  }
}

/**
 * Make HTTP request to ADK agent endpoint
 * @param {string} endpoint - The API endpoint (e.g., ':query')
 * @param {Object} payload - Request payload
 * @param {Object} options - Additional request options
 * @return {Object} Response data
 */
function makeAdkRequest(endpoint, payload = null, options = {}) {
  try {
    const accessToken = getAccessToken();
    const url = CONFIG.BASE_URL + endpoint;
    
    const requestOptions = {
      method: options.method || 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      muteHttpExceptions: true
    };
    
    if (payload) {
      requestOptions.payload = JSON.stringify(payload);
    }
    
    console.log(`Making request to: ${url}`);
    console.log(`Payload:`, JSON.stringify(payload, null, 2));
    
    const response = UrlFetchApp.fetch(url, requestOptions);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    console.log(`Response Code: ${responseCode}`);
    console.log(`Response: ${responseText}`);
    
    if (responseCode >= 400) {
      throw new Error(`HTTP ${responseCode}: ${responseText}`);
    }
    
    return JSON.parse(responseText);
  } catch (error) {
    console.error('Error making ADK request:', error);
    throw error;
  }
}

// SYNCHRONOUS SESSION METHODS

/**
 * Create a new session for a user (synchronous)
 * @param {string} userId - User ID (max 128 characters)
 * @return {Object} Session creation response
 */
function createSession(userId) {
  if (!userId || userId.length > 128) {
    throw new Error('User ID is required and must be 128 characters or less');
  }
  
  const payload = {
    class_method: 'create_session',
    input: {
      user_id: userId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Session created for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error creating session for user ${userId}:`, error);
    throw error;
  }
}

/**
 * List all sessions for a user (synchronous)
 * @param {string} userId - User ID
 * @return {Object} List of sessions
 */
function listSessions(userId) {
  if (!userId) {
    throw new Error('User ID is required');
  }
  
  const payload = {
    class_method: 'list_sessions',
    input: {
      user_id: userId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Listed sessions for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error listing sessions for user ${userId}:`, error);
    throw error;
  }
}

/**
 * Get a specific session (synchronous)
 * @param {string} userId - User ID
 * @param {string} sessionId - Session ID
 * @return {Object} Session details
 */
function getSession(userId, sessionId) {
  if (!userId || !sessionId) {
    throw new Error('Both user ID and session ID are required');
  }
  
  const payload = {
    class_method: 'get_session',
    input: {
      user_id: userId,
      session_id: sessionId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Retrieved session ${sessionId} for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error getting session ${sessionId} for user ${userId}:`, error);
    throw error;
  }
}

// ASYNCHRONOUS SESSION METHODS

/**
 * Create a new session for a user (asynchronous)
 * @param {string} userId - User ID (max 128 characters)
 * @return {Object} Session creation response
 */
function createSessionAsync(userId) {
  if (!userId || userId.length > 128) {
    throw new Error('User ID is required and must be 128 characters or less');
  }
  
  const payload = {
    class_method: 'async_create_session',
    input: {
      user_id: userId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Async session created for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error creating async session for user ${userId}:`, error);
    throw error;
  }
}

/**
 * List all sessions for a user (asynchronous)
 * @param {string} userId - User ID
 * @return {Object} List of sessions
 */
function listSessionsAsync(userId) {
  if (!userId) {
    throw new Error('User ID is required');
  }
  
  const payload = {
    class_method: 'async_list_sessions',
    input: {
      user_id: userId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Async listed sessions for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error async listing sessions for user ${userId}:`, error);
    throw error;
  }
}

/**
 * Get a specific session (asynchronous)
 * @param {string} userId - User ID
 * @param {string} sessionId - Session ID
 * @return {Object} Session details
 */
function getSessionAsync(userId, sessionId) {
  if (!userId || !sessionId) {
    throw new Error('Both user ID and session ID are required');
  }
  
  const payload = {
    class_method: 'async_get_session',
    input: {
      user_id: userId,
      session_id: sessionId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Async retrieved session ${sessionId} for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error async getting session ${sessionId} for user ${userId}:`, error);
    throw error;
  }
}

/**
 * Delete a specific session (asynchronous)
 * @param {string} userId - User ID
 * @param {string} sessionId - Session ID
 * @return {Object} Deletion response
 */
function deleteSessionAsync(userId, sessionId) {
  if (!userId || !sessionId) {
    throw new Error('Both user ID and session ID are required');
  }
  
  const payload = {
    class_method: 'async_delete_session',
    input: {
      user_id: userId,
      session_id: sessionId
    }
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log(`Async deleted session ${sessionId} for user: ${userId}`);
    return response;
  } catch (error) {
    console.error(`Error async deleting session ${sessionId} for user ${userId}:`, error);
    throw error;
  }
}

// FEEDBACK METHOD

/**
 * Register feedback for the agent
 * @param {Object} feedbackData - Feedback data object
 * @return {Object} Feedback registration response
 */
function registerFeedback(feedbackData) {
  if (!feedbackData) {
    throw new Error('Feedback data is required');
  }
  
  const payload = {
    class_method: 'register_feedback',
    input: feedbackData
  };
  
  try {
    const response = makeAdkRequest(':query', payload);
    console.log('Feedback registered successfully');
    return response;
  } catch (error) {
    console.error('Error registering feedback:', error);
    throw error;
  }
}

/**
 * Get ADK application information and available methods
 * @return {Object} Application details
 */
function getAdkApplication() {
  try {
    const accessToken = getAccessToken();
    const url = CONFIG.BASE_URL;
    
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      muteHttpExceptions: true
    });
    
    const result = JSON.parse(response.getContentText());
    console.log('Available methods:', result.spec?.class_methods);
    return result;
  } catch (error) {
    console.error('Error getting ADK application info:', error);
    throw error;
  }
}

// EXAMPLE USAGE FUNCTIONS

/**
 * Example: Complete workflow demonstration
 */
function exampleWorkflow() {
  try {
    const userId = 'example-user-123';
    
    console.log('=== ADK Agent Workflow Example ===');
    
    // 1. Create a session
    console.log('1. Creating session...');
    const createResponse = createSession(userId);
    console.log('Create response:', createResponse);
    
    // Extract session ID from response
    const sessionId = createResponse.output?.session_id || createResponse.session_id;
    
    if (!sessionId) {
      console.log('Could not extract session ID from response. Using async version...');
      const asyncCreateResponse = createSessionAsync(userId);
      console.log('Async create response:', asyncCreateResponse);
    }
    
    // 2. List sessions
    console.log('2. Listing sessions...');
    const listResponse = listSessions(userId);
    console.log('List response:', listResponse);
    
    // 3. Get specific session (if we have a session ID)
    if (sessionId) {
      console.log('3. Getting session details...');
      const getResponse = getSession(userId, sessionId);
      console.log('Get response:', getResponse);
    }
    
    // 4. Register feedback example
    console.log('4. Registering feedback...');
    const feedbackData = {
      user_id: userId,
      rating: 5,
      comment: 'Great service!'
    };
    const feedbackResponse = registerFeedback(feedbackData);
    console.log('Feedback response:', feedbackResponse);
    
    // 5. Clean up - delete session (if we have a session ID)
    if (sessionId) {
      console.log('5. Cleaning up - deleting session...');
      const deleteResponse = deleteSessionAsync(userId, sessionId);
      console.log('Delete response:', deleteResponse);
    }
    
    console.log('=== Workflow completed successfully ===');
    
  } catch (error) {
    console.error('Error in example workflow:', error);
  }
}

/**
 * Example: Simple session creation and listing
 */
function exampleSimpleSessionManagement() {
  try {
    const userId = 'simple-user-456';
    
    console.log('=== Simple Session Management Example ===');
    
    // Create a session
    console.log('Creating session...');
    const createResponse = createSession(userId);
    console.log('Session created:', createResponse);
    
    // List sessions
    console.log('Listing sessions...');
    const listResponse = listSessions(userId);
    console.log('Sessions:', listResponse);
    
  } catch (error) {
    console.error('Error in simple session management example:', error);
  }
}

/**
 * Test available methods by getting application info
 */
function testAvailableMethods() {
  try {
    console.log('=== Testing Available Methods ===');
    const appInfo = getAdkApplication();
    console.log('Application Info:', JSON.stringify(appInfo, null, 2));
    
    if (appInfo.spec && appInfo.spec.class_methods) {
      console.log('Available methods:');
      appInfo.spec.class_methods.forEach(method => {
        console.log(`- ${method}`);
      });
    }
    
  } catch (error) {
    console.error('Error testing available methods:', error);
  }
}

/**
 * Utility function to test configuration
 */
function testConfiguration() {
  try {
    console.log('=== Testing Configuration ===');
    console.log('Project ID:', CONFIG.PROJECT_ID);
    console.log('Location:', CONFIG.LOCATION);
    console.log('Resource ID:', CONFIG.RESOURCE_ID);
    console.log('Base URL:', CONFIG.BASE_URL);
    
    console.log('Testing authentication...');
    const token = getAccessToken();
    console.log('Authentication successful');
    
    console.log('Testing ADK application access...');
    testAvailableMethods();
    
    console.log('=== Configuration test completed ===');
    
  } catch (error) {
    console.error('Configuration test failed:', error);
    console.error('Please check your CONFIG settings and OAuth configuration');
  }
}

/**
 * Setup instructions (run this first)
 */
function setupInstructions() {
  console.log(`
=== SETUP INSTRUCTIONS ===

1. Update the CONFIG object at the top of this script:
   - PROJECT_ID: Your Google Cloud project ID
   - LOCATION: Your preferred location (e.g., 'us-central1')
   - RESOURCE_ID: Your reasoning engine resource ID

2. Configure OAuth scopes in Google Apps Script:
   - Go to the Apps Script editor
   - Click on 'Services' in the left sidebar
   - Add the Google Cloud Platform API
   - Set the required OAuth scopes for Google Cloud access

3. Test your configuration:
   - Run the testConfiguration() function
   - Run testAvailableMethods() to see what methods are available
   - Ensure all tests pass before proceeding

4. Try the examples:
   - Run exampleSimpleSessionManagement() for a basic test
   - Run exampleWorkflow() for a complete demonstration

=== AVAILABLE METHODS ===
Based on your agent, these methods are available:
- createSession() / createSessionAsync()
- listSessions() / listSessionsAsync() 
- getSession() / getSessionAsync()
- deleteSessionAsync()
- registerFeedback()

=== READY TO USE ===
  `);
}

/**
 * Test different query methods to find the correct one
 * @param {string} userId - User ID
 * @param {string} message - Test message
 * @param {string} sessionId - Optional session ID
 */
function discoverQueryMethod(userId, message = "Hello, how can you help me?", sessionId = null) {
  console.log('=== Discovering Query Method ===');
  
  // List of possible query method names to try
  const possibleQueryMethods = [
    'query',
    'chat',
    'ask',
    'send_message',
    'process_query',
    'handle_query',
    'stream_query', // Even though it failed, let's try again
    'async_query',
    'async_chat',
    'conversation',
    'interact'
  ];
  
  for (const methodName of possibleQueryMethods) {
    try {
      console.log(`Trying method: ${methodName}`);
      
      const payload = {
        class_method: methodName,
        input: {
          user_id: userId,
          message: message
        }
      };
      
      // Add session ID if provided
      if (sessionId) {
        payload.input.session_id = sessionId;
      }
      
      const response = makeAdkRequest(':query', payload);
      console.log(`✅ SUCCESS with method: ${methodName}`);
      console.log('Response:', response);
      return { method: methodName, response: response };
      
    } catch (error) {
      console.log(`❌ Failed with method: ${methodName}`);
      console.log('Error:', error.message);
    }
  }
  
  console.log('❌ No query method found among common names');
  return null;
}

/**
 * Try querying using different endpoints
 * @param {string} userId - User ID  
 * @param {string} message - Test message
 * @param {string} sessionId - Optional session ID
 */
function tryDifferentEndpoints(userId, message = "Hello", sessionId = null) {
  console.log('=== Trying Different Endpoints ===');
  
  const endpoints = [
    ':query',
    ':streamQuery',
    ':streamQuery?alt=sse',
    ':chat',
    ':ask',
    ':process'
  ];
  
  const payload = {
    class_method: 'query', // Try with generic 'query'
    input: {
      user_id: userId,
      message: message
    }
  };
  
  if (sessionId) {
    payload.input.session_id = sessionId;
  }
  
  for (const endpoint of endpoints) {
    try {
      console.log(`Trying endpoint: ${endpoint}`);
      const response = makeAdkRequest(endpoint, payload);
      console.log(`✅ SUCCESS with endpoint: ${endpoint}`);
      console.log('Response:', response);
      return { endpoint: endpoint, response: response };
      
    } catch (error) {
      console.log(`❌ Failed with endpoint: ${endpoint}`);
      console.log('Error:', error.message);
    }
  }
  
  console.log('❌ No working endpoint found');
  return null;
}

/**
 * Check if query functionality is built into session operations
 * @param {string} userId - User ID
 * @param {string} message - Test message
 */
function testSessionWithMessage(userId, message = "Hello") {
  console.log('=== Testing Session Creation with Message ===');
  
  try {
    // Try creating session with message
    const payload = {
      class_method: 'create_session',
      input: {
        user_id: userId,
        initial_message: message // Maybe sessions accept initial messages?
      }
    };
    
    const response = makeAdkRequest(':query', payload);
    console.log('✅ Session created with message');
    console.log('Response:', response);
    return response;
    
  } catch (error) {
    console.log('❌ Session creation with message failed');
    console.log('Error:', error.message);
  }
  
  try {
    // Try different session input formats
    const payload2 = {
      class_method: 'create_session',
      input: {
        user_id: userId,
        message: message,
        context: "chat_session"
      }
    };
    
    const response2 = makeAdkRequest(':query', payload2);
    console.log('✅ Session created with context and message');
    console.log('Response:', response2);
    return response2;
    
  } catch (error) {
    console.log('❌ Session creation with context failed');
    console.log('Error:', error.message);
  }
  
  return null;
}

/**
 * Comprehensive query discovery test
 * @param {string} userId - User ID for testing
 */
function findQueryMethod(userId = 'test-user-query-discovery') {
  console.log('=== COMPREHENSIVE QUERY METHOD DISCOVERY ===');
  
  try {
    // Step 1: Get available methods
    console.log('Step 1: Checking available methods...');
    const appInfo = getAdkApplication();
    if (appInfo.spec?.class_methods) {
      console.log('Available methods:', appInfo.spec.class_methods);
    }
    
    // Step 2: Create a session first
    console.log('Step 2: Creating a session...');
    const sessionResponse = createSession(userId);
    console.log('Session created:', sessionResponse);
    
    const sessionId = sessionResponse.output?.session_id || sessionResponse.session_id;
    console.log('Extracted session ID:', sessionId);
    
    // Step 3: Try different query methods
    console.log('Step 3: Testing query methods...');
    const queryResult = discoverQueryMethod(userId, "Hello, how can you help me?", sessionId);
    
    if (queryResult) {
      console.log(`🎉 Found working query method: ${queryResult.method}`);
      return queryResult;
    }
    
    // Step 4: Try different endpoints
    console.log('Step 4: Testing different endpoints...');
    const endpointResult = tryDifferentEndpoints(userId, "Hello", sessionId);
    
    if (endpointResult) {
      console.log(`🎉 Found working endpoint: ${endpointResult.endpoint}`);
      return endpointResult;
    }
    
    // Step 5: Test session-based messaging
    console.log('Step 5: Testing session-based messaging...');
    const sessionResult = testSessionWithMessage(userId, "Hello");
    
    if (sessionResult) {
      console.log('🎉 Found session-based messaging');
      return { method: 'session_based', response: sessionResult };
    }
    
    console.log('❌ No query method discovered');
    console.log('💡 Suggestions:');
    console.log('1. Check your ADK agent implementation');
    console.log('2. Verify the agent has query/chat functionality');
    console.log('3. Contact the agent developer for the correct method name');
    
  } catch (error) {
    console.error('Error during query discovery:', error);
  }
  
  return null;
}

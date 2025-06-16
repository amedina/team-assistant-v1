# Firebase Studio Prompt: Multi-Agent Team Assistant WebUI

## Project Overview
Create a modern, responsive WebUI frontend that serves as the primary interface to a unified Team Assistant system. This is a **multi-tenant application** where each user has their own private, independent conversations with the Team Assistant. The application should provide an intuitive conversational interface where users interact with a single, intelligent Team Assistant that automatically coordinates with specialized sub-agents behind the scenes to provide comprehensive support for strategic planning and tactical execution. The frontend will communicate with the Team Assistant system exclusively through REST API calls and contains **no AI capabilities of its own**.

## Core Requirements

### 0. Multi-Tenant Application Architecture
- **Individual User Sessions**: Each user has their own private conversations with the Team Assistant
- **User Isolation**: Complete separation of user data - User A's conversations are independent from User B's
- **Private Conversations**: Each user's chat history and data should be isolated and secure
- **Independent Authentication**: Multiple users can sign up and use the app independently
- **Personal Workspaces**: Each user has their own conversation history and workspace
- **User-Specific API Calls**: REST API calls include user context for personalized Team Assistant interactions

### 1. Application Architecture
- **Framework**: Next.js 14+ with TypeScript and App Router
- **Styling**: Tailwind CSS for responsive design
- **State Management**: React Context or Zustand for user session and conversation state
- **Real-time Communication**: Firebase Realtime Database or Firestore for user-specific conversation history
- **API Routes**: Next.js API routes for server-side Team Assistant communication

### 2. Firebase Services Integration
- **Authentication**: Firebase Auth with Google/email sign-in
- **Database**: Firestore for storing user-specific conversations, tasks, and preferences
- **Data Structure**: User-isolated data (`/users/{userId}/conversations/{conversationId}/messages`)
- **Hosting**: Firebase Hosting with Next.js static export or Firebase Functions for SSR
- **Functions**: Firebase Functions for backend Team Assistant communication APIs
- **Security**: Firestore Security Rules for strict user data isolation
- **API Integration**: Next.js API routes for seamless server-client communication

### 3. Core UI Components

#### Dashboard Layout
- **Header**: Navigation bar with user profile, notifications, and Team Assistant status
- **Sidebar**: Conversation history, team workspaces, and quick actions
- **Main Content Area**: Primary chat interface with the Team Assistant
- **Activity Panel**: Real-time insights into Team Assistant processing and sub-agent coordination

#### Team Assistant Interface Components
- **Unified Chat Interface**: Clean conversation UI supporting text, files, and rich media responses
- **Processing Indicators**: Visual feedback showing Team Assistant thinking and sub-agent coordination
- **Response Attribution**: Subtle indicators showing which capabilities were used (optional transparency)
- **Task Management**: Integration with Team Assistant-generated tasks and recommendations
- **Simple Context Storage**: Frontend stores conversation history locally and sends relevant context to Team Assistant API (no AI processing in frontend)

#### Individual User Features
- **Personal Workspaces**: Individual conversation spaces for each user
- **Conversation History**: User-specific chat history and search capabilities  
- **Personal Task Management**: Individual task lists and recommendations from Team Assistant
- **Document Management**: Personal file upload and sharing with Team Assistant
- **User Preferences**: Individual settings and customization options

### 4. Team Assistant System Integration

#### REST API Communication
- **Team Assistant Interface**: Primary endpoints for unified conversation with the Team Assistant
- **Session Management**: API calls for creating, managing, and closing conversation sessions
- **Query Processing**: POST endpoints for sending user questions and receiving intelligent responses
- **Task Management**: REST endpoints for creating, updating, and tracking assistant-generated tasks
- **Real-time Updates**: Polling or webhook integration for live processing status and response updates

#### Unified Team Assistant Capabilities
The Team Assistant automatically coordinates these capabilities behind the scenes:
- Strategic Planning and Analysis
- Tactical Execution Support
- Research and Information Gathering
- Communication and Coordination
- Project Management and Tracking
- (Extensible capability addition through system updates)

#### Communication Features
- **User-to-Assistant**: Primary conversation interface with intelligent response routing
- **Sub-Agent Coordination**: Background orchestration (optionally visible to users for transparency)
- **Contextual Responses**: Team Assistant maintains conversation context across different capability areas
- **Seamless Experience**: No manual agent switching - the Team Assistant handles all coordination

### 5. User Experience Requirements

#### Core UX Principles
- **Intuitive Navigation**: Clear visual hierarchy and logical flow
- **Real-time Feedback**: Live typing indicators, agent status, and progress updates
- **Mobile Responsive**: Optimized for desktop, tablet, and mobile devices
- **Accessibility**: WCAG 2.1 compliant with keyboard navigation and screen reader support

#### Advanced Features
- **Smart Notifications**: Contextual alerts for agent updates and team activities
- **Search Functionality**: Global search across conversations and documents
- **Customizable Workspace**: User preferences for layout and agent visibility
- **Dark/Light Mode**: Theme switching with system preference detection

### 6. Technical Specifications

#### Performance Requirements
- **Loading Time**: Initial load under 3 seconds
- **Real-time Updates**: Sub-second message delivery
- **Offline Capability**: Basic offline viewing with sync on reconnection
- **Scalability**: Support for teams of 10-100+ users

#### Security & Privacy
- **User Authentication**: Secure login with role-based access
- **Data Encryption**: End-to-end encryption for sensitive conversations
- **Team Isolation**: Strict data separation between different teams
- **Audit Logging**: Comprehensive activity tracking for compliance

### 7. Team Assistant API Integration

#### Expected API Endpoints Structure
```typescript
// Team Assistant Interaction
POST /api/assistant/sessions -> Create new conversation session
POST /api/assistant/sessions/{sessionId}/messages -> Send message to Team Assistant
GET /api/assistant/sessions/{sessionId}/messages -> Retrieve conversation history
GET /api/assistant/sessions/{sessionId}/context -> Get current conversation context

// System Status
GET /api/assistant/status -> Team Assistant availability and system health
GET /api/assistant/capabilities -> Available Team Assistant capabilities

// Task Management
GET /api/sessions/{sessionId}/tasks -> Get assistant-generated tasks
PUT /api/tasks/{taskId} -> Update task status
POST /api/sessions/{sessionId}/tasks -> Create new task

// Optional Transparency Features
GET /api/sessions/{sessionId}/processing -> Real-time sub-agent coordination insights (optional)
```

#### API Client Requirements
- **Unified Interface**: Single API client for all Team Assistant interactions
- **Type Safety**: TypeScript interfaces for all API requests and responses
- **Authentication**: Bearer token or API key integration for secure assistant access
- **Conversation Context**: Maintain session state and context across interactions
- **Processing Status**: Real-time updates on Team Assistant thinking and response generation
- **Error Recovery**: Graceful handling of processing delays and system errors

### 8. Development Deliverables

#### Phase 1: Core Foundation
1. Project setup with Firebase configuration
2. Authentication system with individual user management
3. Basic chat interface with Team Assistant interaction
4. Responsive layout with navigation components
5. User-isolated data structure in Firestore

#### Phase 2: Enhanced Team Assistant Features
1. Simple conversation context storage and API transmission (no AI processing)
2. Real-time processing indicators and status updates
3. Personal task management integration with Team Assistant
4. File sharing and document analysis capabilities for individual users

#### Phase 3: Individual User Features
1. Personal workspace customization and preferences
2. Individual conversation history and search functionality
3. Personal analytics dashboard and usage reporting
4. Advanced individual customization options

### 9. Code Structure Preferences
- **Component Organization**: Feature-based folder structure with Next.js App Router
- **State Management**: Centralized state for individual user conversations and context storage
- **API Integration**: 
  - Next.js API routes as proxy layer to Team Assistant REST APIs
  - Dedicated service layer for Team Assistant API communication
  - Type-safe API client with TypeScript interfaces for assistant responses
  - Simple conversation context storage and transmission (NO AI processing in frontend)
  - Error handling and retry logic for Team Assistant API calls
- **Error Handling**: Comprehensive error boundaries and user feedback for API failures
- **Testing**: Unit tests for critical components, API integration tests, and conversation flows
- **Performance**: Next.js built-in optimizations + response caching strategies for individual conversation history

### 10. Frontend AI Capabilities Clarification
**IMPORTANT: The frontend should contain ZERO AI capabilities and NO intelligent processing.**

**What the frontend SHOULD do:**
- Store conversation history in React state and/or Firestore
- Send user messages + conversation context to Team Assistant API
- Receive and display responses from Team Assistant
- Manage user sessions and authentication
- Provide UI for file uploads and downloads

**What the frontend should NOT do:**
- Any AI processing or intelligent analysis
- Context analysis or assessment
- Decision making about which information to include
- Natural language processing
- Intelligent routing or capability determination

**Context Management Example:**
```javascript
// CORRECT: Simple data storage and transmission
const sendMessage = async (userMessage) => {
  const context = {
    conversationHistory: messages, // simple array storage
    userId: currentUser.id,
    sessionId: currentSession.id
  };
  
  const response = await fetch('/api/assistant/messages', {
    method: 'POST',
    body: JSON.stringify({ message: userMessage, context })
  });
  
  // Team Assistant backend does all intelligent processing
  const assistantResponse = await response.json();
  setMessages([...messages, userMessage, assistantResponse]);
};
```

### 11. Design Guidelines
- **Color Scheme**: Professional palette with high contrast for accessibility
- **Typography**: Clean, readable fonts optimized for conversation interfaces
- **Iconography**: Consistent icon system for agents and actions
- **Animation**: Subtle transitions and loading states for smooth UX

## Expected Output
Please generate a complete Firebase project structure including:
- Next.js application with App Router and TypeScript configuration
- React components for unified Team Assistant conversation interface
- Firebase configuration and service setup
- Firestore data models and security rules
- Authentication flow implementation with Next.js middleware
- Responsive CSS with Tailwind classes
- **Team Assistant Integration**:
  - TypeScript API client for Team Assistant REST endpoints
  - Next.js API routes as proxy layer to Team Assistant system
  - Type-safe interfaces for unified assistant interactions
  - Conversation context management and session handling
  - Error handling and retry logic for API communication
- Deployment configuration for Firebase Hosting (static export or SSR setup)

## Additional Context
The Team Assistant system is an existing, intelligent system that presents a unified interface while internally coordinating with specialized sub-agents. The frontend should be designed as a clean conversational interface for **individual users with private conversations** that:

- **Multi-Tenant Architecture**: Each user has completely isolated, private conversations with the Team Assistant
- **No AI Capabilities**: Frontend is purely a user interface with no intelligent processing whatsoever
- **Simple Data Handling**: Frontend stores conversation history and passes it to Team Assistant API
- **Unified Experience**: Users interact with a single "Team Assistant" entity, not individual agents
- **Intelligent Routing**: The Team Assistant (backend) automatically determines which capabilities to use for each query
- **API Communication**: Makes RESTful HTTP requests to the Team Assistant endpoints with user context
- **Response Handling**: Processes unified JSON responses that may contain insights from multiple sub-agents
- **Session Management**: Maintains individual user conversation context while the Team Assistant coordinates behind the scenes
- **Processing Transparency**: Optionally shows users what capabilities are being engaged (without overwhelming them)
- **Error Recovery**: Gracefully handles API timeouts and system processing delays

**Data Isolation Example:**
```
/users/{userId}/conversations/{conversationId}/messages
/users/{userId}/tasks
/users/{userId}/preferences
/users/{userId}/files
```

The frontend should provide an intuitive, ChatGPT-like experience where individual users simply ask questions and receive intelligent, comprehensive responses from their personal Team Assistant.
# Firebase Studio Prompt: Multi-Agent Team Assistant WebUI

## Project Overview
Create a modern, responsive WebUI frontend that serves as the primary interface to a unified Team Assistant system. The application should provide an intuitive conversational interface where users interact with a single, intelligent Team Assistant that automatically coordinates with specialized sub-agents behind the scenes to provide comprehensive support for strategic planning and tactical execution. The frontend will communicate with the Team Assistant system exclusively through REST API calls.

## Core Requirements

### 1. Application Architecture
- **Framework**: Next.js 14+ with TypeScript and App Router
- **Styling**: Tailwind CSS for responsive design
- **State Management**: React Context or Zustand for agent communication state
- **Real-time Communication**: Firebase Realtime Database or Firestore for live agent updates
- **API Routes**: Next.js API routes for server-side agent communication

### 2. Firebase Services Integration
- **Authentication**: Firebase Auth with Google/email sign-in
- **Database**: Firestore for storing conversations, agent configurations, and team data
- **Hosting**: Firebase Hosting with Next.js static export or Firebase Functions for SSR
- **Functions**: Firebase Functions for backend agent communication APIs
- **Security**: Firestore Security Rules for user data protection
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
- **Context Awareness**: Interface elements that show the Team Assistant's understanding of ongoing projects

#### Team Collaboration Features
- **Shared Workspaces**: Team-level conversation spaces
- **Task Management**: Integration with agent-generated tasks and recommendations
- **Document Sharing**: File upload and sharing capabilities
- **Team Analytics**: Performance metrics and usage statistics

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
2. Authentication system with user management
3. Basic chat interface with Team Assistant interaction
4. Responsive layout with navigation components

#### Phase 2: Enhanced Team Assistant Features
1. Advanced conversation context management
2. Real-time processing indicators and status updates
3. Task management integration with Team Assistant
4. File sharing and document analysis capabilities

#### Phase 3: Team Collaboration
1. Team workspace creation and management
2. Shared conversations and collaborative features with Team Assistant
3. Analytics dashboard and usage reporting
4. Advanced customization and preference options

### 9. Code Structure Preferences
- **Component Organization**: Feature-based folder structure with Next.js App Router
- **State Management**: Centralized state for Team Assistant conversations and context management
- **API Integration**: 
  - Next.js API routes as proxy layer to Team Assistant REST APIs
  - Dedicated service layer for Team Assistant API communication
  - Type-safe API client with TypeScript interfaces for assistant responses
  - Conversation context persistence and session management
  - Error handling and retry logic for Team Assistant API calls
- **Error Handling**: Comprehensive error boundaries and user feedback for API failures
- **Testing**: Unit tests for critical components, API integration tests, and conversation flows
- **Performance**: Next.js built-in optimizations + response caching strategies for conversation history

### 10. Design Guidelines
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
The Team Assistant system is an existing, intelligent system that presents a unified interface while internally coordinating with specialized sub-agents. The frontend should be designed as a clean conversational interface that:

- **Unified Experience**: Users interact with a single "Team Assistant" entity, not individual agents
- **Intelligent Routing**: The Team Assistant automatically determines which capabilities to use for each query
- **API Communication**: Makes RESTful HTTP requests to the Team Assistant endpoints
- **Response Handling**: Processes unified JSON responses that may contain insights from multiple sub-agents
- **Session Management**: Maintains conversation context while the Team Assistant coordinates behind the scenes
- **Processing Transparency**: Optionally shows users what capabilities are being engaged (without overwhelming them)
- **Error Recovery**: Gracefully handles API timeouts and system processing delays

The frontend should provide an intuitive, ChatGPT-like experience where users simply ask questions and receive intelligent, comprehensive responses from their Team Assistant.
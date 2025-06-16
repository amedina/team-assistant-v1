# Firebase Studio Prompt: Multi-Agent Team Assistant WebUI

## Project Overview
Create a modern, responsive WebUI frontend for a multi-agent Team Assistant system. The application should provide an intuitive interface for users to interact with various specialized AI agents that support strategic planning and tactical execution for teams.

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
- **Header**: Navigation bar with user profile, notifications, and agent status indicators
- **Sidebar**: Agent selector panel with available agents and their specializations
- **Main Content Area**: Primary interaction space with chat interface
- **Status Panel**: Real-time system status and agent availability

#### Agent Interface Components
- **Agent Cards**: Visual representation of each agent with capabilities and status
- **Chat Interface**: Clean conversation UI supporting text, files, and rich media
- **Agent Switcher**: Seamless switching between different specialized agents
- **Task Queue**: Visual representation of ongoing and pending agent tasks

#### Team Collaboration Features
- **Shared Workspaces**: Team-level conversation spaces
- **Task Management**: Integration with agent-generated tasks and recommendations
- **Document Sharing**: File upload and sharing capabilities
- **Team Analytics**: Performance metrics and usage statistics

### 4. Multi-Agent System Integration

#### Agent Types to Support
- Strategic Planning Agent
- Tactical Execution Agent
- Research & Analysis Agent
- Communication Coordinator
- Project Management Agent
- (Allow for extensible agent addition)

#### Communication Features
- **Agent-to-User**: Direct conversation interface
- **Agent-to-Agent**: Background coordination (visible to users)
- **Multi-Agent Conversations**: Collaborative sessions with multiple agents
- **Agent Handoffs**: Smooth transitions between agents for complex tasks

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

### 7. Development Deliverables

#### Phase 1: Core Foundation
1. Project setup with Firebase configuration
2. Authentication system with user management
3. Basic chat interface with single agent interaction
4. Responsive layout with navigation components

#### Phase 2: Multi-Agent Features
1. Agent management system with multiple agent types
2. Real-time multi-agent conversations
3. Task queue and status management
4. File sharing and document management

#### Phase 3: Team Collaboration
1. Team workspace creation and management
2. Shared conversations and collaborative features
3. Analytics dashboard and reporting
4. Advanced customization options

### 8. Code Structure Preferences
- **Component Organization**: Feature-based folder structure with Next.js App Router
- **State Management**: Centralized state for agent communication
- **API Integration**: Next.js API routes for clean server-side agent communication
- **Error Handling**: Comprehensive error boundaries and user feedback
- **Testing**: Unit tests for critical components and user flows
- **Performance**: Next.js built-in optimizations (Image, Font, Bundle optimization)

### 9. Design Guidelines
- **Color Scheme**: Professional palette with high contrast for accessibility
- **Typography**: Clean, readable fonts optimized for conversation interfaces
- **Iconography**: Consistent icon system for agents and actions
- **Animation**: Subtle transitions and loading states for smooth UX

## Expected Output
Please generate a complete Firebase project structure including:
- Next.js application with App Router and TypeScript configuration
- React components for all specified UI elements
- Firebase configuration and service setup
- Firestore data models and security rules
- Authentication flow implementation with Next.js middleware
- Responsive CSS with Tailwind classes
- Next.js API routes for agent communication interfaces
- Deployment configuration for Firebase Hosting (static export or SSR setup)

## Additional Context
The multi-agent system backend will communicate via REST APIs and WebSocket connections. The frontend should be designed to easily integrate with various agent services while providing a unified, intuitive user experience for team collaboration and AI-assisted work.
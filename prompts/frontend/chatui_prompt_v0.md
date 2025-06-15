# AI Code Assistant: Build Agent System Frontend with ChatUI

## Project Overview
I'm building a front-end interface for my agent system running on Agent Engine. I want to use ChatUI as the foundation and create a composable web UI experience similar to Super Apps/Mini Apps architecture, where the chat interface serves as the "Super App" and individual agent components function as "Mini Apps."

## Your Mission
Help me understand, modify, and extend ChatUI to create a production-ready agent system interface. I need comprehensive guidance from setup to deployment.

## Phase 1: Deep Analysis & Understanding
**First, please thoroughly analyze the ChatUI project:**

1. **Project Structure Analysis**
   - Clone and examine the ChatUI repository structure
   - Document the key directories, files, and their purposes
   - Identify the core components and their relationships
   - Map out the data flow and state management patterns
   - Explain the authentication system and user management

2. **Architecture Deep Dive**
   - Analyze the current tech stack and dependencies
   - Document the API structure and endpoints
   - Understand the database schema and relationships
   - Identify extension points for custom functionality
   - Review the styling/theming system

3. **Feature Analysis**
   - Document all existing features and capabilities
   - Identify which features align with my agent system vision
   - Highlight areas that need modification or extension

## Phase 2: Technology Stack Decisions
**Help me make informed decisions about:**

1. **Frontend Framework**: Confirm Next.js setup and best practices
2. **UI Library**: 
   - Evaluate shadcn/ui integration vs. ChatUI's current UI system
   - Pros/cons of migration
   - Implementation strategy if we proceed
   - Component compatibility analysis

3. **Database Strategy**: 
   - The ChatUI repo suggests Supabase, but I want to use my own cloud-based database
   - My DB is a PostgreSQL; what are the requirements to use my own PostgreSQL DB?
   - Design migration strategy from Supabase to chosen solution
   - Ensure compatibility with agent system requirements

## Phase 3: Super App Architecture Design
**This is the key differentiator - help me design:**

The baseline, fully functional chat bot, is the main entry point to my application. UI components associated with different agents can be added in a composable manner. 

1. **Composable Component System**
   - Design plugin/widget architecture for agent components
   - Create standard interfaces for agent integration
   - Plan component lifecycle management
   - Design inter-component communication patterns

2. **Agent Integration Framework**
   - Design API layer for Agent Engine communication
   - Plan real-time updates and streaming responses
   - Create standard agent component templates
   - Design agent discovery and registration system

3. **Mini App Container System**
   - Create iframe-like containers for agent UIs
   - Design security boundaries between components
   - Plan resource sharing and state management
   - Create standard APIs for Mini App interactions

## Phase 4: Implementation Roadmap
**Provide a step-by-step implementation plan:**

1. **Environment Setup**
   - Detailed setup instructions for development environment
   - Configuration of all necessary tools and dependencies
   - Database setup and migration procedures

2. **Base Implementation**
   - Fork and modify ChatUI codebase
   - Implement chosen UI library (shadcn/ui if recommended)
   - Set up cloud database integration
   - Ensure basic chat functionality works

3. **Agent System Integration**
   - Implement Agent Engine API connectivity
   - Create first sample agent component
   - Build the Mini App container system
   - Test end-to-end agent communication

4. **Advanced Features**
   - Multi-agent orchestration
   - Component state persistence
   - Advanced UI interactions
   - Performance optimization

## Relevant links

   - ChatUO Github repository: @https://github.com/mckaywrigley/chatbot-ui

## Key Requirements & Constraints

- **Framework**: Must use Next.js
- **UI Consistency**: Professional, modern interface
- **Scalability**: Support multiple concurrent agents
- **Modularity**: Easy to add/remove agent components
- **Performance**: Fast loading and responsive interactions
- **Security**: Proper isolation between agent components
- **Developer Experience**: Easy for other developers to extend

## Expected Deliverables

For each phase, provide:
1. **Detailed explanations** of concepts and decisions
2. **Complete code examples** with best practices
3. **Step-by-step tutorials** I can follow
4. **Troubleshooting guides** for common issues
5. **Testing strategies** for each component
6. **Documentation templates** for future development

## Success Criteria

By the end of this project, I should have:
- A fully functional chat interface based on ChatUI
- A working agent component system
- At least one sample agent integration
- Clear documentation for extending the system
- A deployment-ready application

## Communication Style
- Explain complex concepts clearly with examples
- Provide code with detailed comments
- Suggest best practices and alternatives
- Ask clarifying questions when needed
- Break down large tasks into manageable steps

# Deliverable Requirements

Follow these steps:

Explain Your Plan:
Begin by outlining the steps you plan to take to implement the feature or solve the issue. Be clear and concise.

Present Options:
Provide a few different options for how the task can be accomplished. Explain the pros and cons of each option.

Request User Input:
Ask the user to choose one of the options or provide their own.

Based on the user's input ({user_choice}), develop your plan of action.

**Let's start with Phase 1: Analyze the ChatUI project structure and provide me with a comprehensive overview of what we're working with.**
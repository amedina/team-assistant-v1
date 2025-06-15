// Layout component that matches your described UI pattern
import React from 'react';
import { useAppStore } from './store/appStore';
import { AgentSidebar } from './components/AgentSidebar';
import { AgentWorkspace } from './components/AgentWorkspace';
import { ChatInterface } from './components/ChatInterface';

export const AgentChatLayout: React.FC = () => {
  const { 
    activeAgents, 
    agentRegistry, 
    activateAgent, 
    deactivateAgent 
  } = useAppStore();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Agent List */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Agents</h2>
        </div>
        
        <AgentSidebar
          availableAgents={agentRegistry.getAllAgents()}
          activeAgents={Array.from(activeAgents.values())}
          onActivateAgent={activateAgent}
          onDeactivateAgent={deactivateAgent}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Active Agent UI Area - Above Chat */}
        <div className="flex-1 bg-white border-b border-gray-200 overflow-hidden">
          {activeAgents.size > 0 ? (
            <AgentWorkspace
              agents={Array.from(activeAgents.values())}
              layout="stacked" // or "grid" for multiple agents
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <div className="text-2xl mb-2">🤖</div>
                <p>Select an agent from the sidebar to get started</p>
              </div>
            </div>
          )}
        </div>

        {/* Chat Interface - Fixed at Bottom */}
        <div className="h-32 bg-white border-t border-gray-200">
          <ChatInterface
            activeAgents={Array.from(activeAgents.keys())}
            onSendMessage={(message, agentId) => {
              // Handle message sending to specific agent or general chat
            }}
          />
        </div>
      </div>
    </div>
  );
};

// Agent Sidebar Component
export const AgentSidebar: React.FC<{
  availableAgents: AgentComponent[];
  activeAgents: AgentInstance[];
  onActivateAgent: (agentId: string) => void;
  onDeactivateAgent: (agentId: string) => void;
}> = ({ availableAgents, activeAgents, onActivateAgent, onDeactivateAgent }) => {
  const activeAgentIds = new Set(activeAgents.map(a => a.id));

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-2">
      {availableAgents.map(agent => (
        <div
          key={agent.id}
          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
            activeAgentIds.has(agent.id)
              ? 'bg-blue-50 border-blue-200 text-blue-900'
              : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
          }`}
          onClick={() => {
            if (activeAgentIds.has(agent.id)) {
              onDeactivateAgent(agent.id);
            } else {
              onActivateAgent(agent.id);
            }
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-sm">{agent.name}</h3>
              <p className="text-xs text-gray-600 mt-1">{agent.description}</p>
            </div>
            <div className="flex items-center space-x-2">
              {activeAgentIds.has(agent.id) && (
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
              )}
              <span className="text-xs text-gray-500">v{agent.version}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Agent Workspace - Renders active agent UIs
export const AgentWorkspace: React.FC<{
  agents: AgentInstance[];
  layout: 'stacked' | 'grid';
}> = ({ agents, layout }) => {
  if (agents.length === 0) return null;

  return (
    <div className="h-full p-4 overflow-auto">
      {layout === 'stacked' ? (
        <div className="space-y-4">
          {agents.map(agent => (
            <AgentContainer
              key={agent.id}
              agentId={agent.id}
              config={agent.config}
              onClose={() => {/* handle close */}}
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
          {agents.map(agent => (
            <AgentContainer
              key={agent.id}
              agentId={agent.id}
              config={agent.config}
              onClose={() => {/* handle close */}}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Enhanced Chat Interface with Agent Context
export const ChatInterface: React.FC<{
  activeAgents: string[];
  onSendMessage: (message: string, agentId?: string) => void;
}> = ({ activeAgents, onSendMessage }) => {
  const [message, setMessage] = React.useState('');
  const [selectedAgent, setSelectedAgent] = React.useState<string>('');

  const handleSend = () => {
    if (!message.trim()) return;
    
    onSendMessage(message, selectedAgent || undefined);
    setMessage('');
  };

  return (
    <div className="h-full flex flex-col p-4">
      {/* Agent Context Selector */}
      {activeAgents.length > 0 && (
        <div className="mb-2">
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="text-sm border rounded px-2 py-1 bg-white"
          >
            <option value="">Send to all agents</option>
            {activeAgents.map(agentId => (
              <option key={agentId} value={agentId}>
                Send to {agentId}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Message Input */}
      <div className="flex space-x-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder={
            selectedAgent 
              ? `Message ${selectedAgent}...` 
              : "Type your message..."
          }
          className="flex-1 border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={!message.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
};
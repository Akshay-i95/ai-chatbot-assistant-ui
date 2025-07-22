import React, { useState, useEffect } from 'react';
import { Thread } from '@assistant-ui/react';
import { apiService, type ChatSession, type ChatMessage } from '../lib/api';
import { ChatHistory } from './ChatHistory';
import { SystemStatus } from './SystemStatus';
import { FileUpload } from './FileUpload';
import { Button } from './ui/button';
import { Sidebar } from './Sidebar';
import { Menu, X, MessageSquare, Upload, Settings, Info } from 'lucide-react';

interface AppState {
  sessions: ChatSession[];
  currentSession: string | null;
  messages: ChatMessage[];
  sidebarOpen: boolean;
  systemReady: boolean;
  loading: boolean;
}

export function ChatInterface() {
  const [state, setState] = useState<AppState>({
    sessions: [],
    currentSession: null,
    messages: [],
    sidebarOpen: true,
    systemReady: false,
    loading: true,
  });

  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'status'>('chat');

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));

      // Check system health
      const health = await apiService.healthCheck();
      const systemReady = health.system_ready;

      // Load chat sessions
      const sessions = await apiService.getChatSessions();

      setState(prev => ({
        ...prev,
        sessions,
        systemReady,
        loading: false,
      }));

      // Auto-select the most recent session or create a new one
      if (sessions.length > 0) {
        await loadSession(sessions[0].id);
      } else {
        await createNewSession();
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
      setState(prev => ({ ...prev, loading: false, systemReady: false }));
    }
  };

  const createNewSession = async (title?: string) => {
    try {
      const session = await apiService.createChatSession(title);
      setState(prev => ({
        ...prev,
        sessions: [session, ...prev.sessions],
        currentSession: session.id,
        messages: [],
      }));
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      const data = await apiService.getChatSession(sessionId);
      setState(prev => ({
        ...prev,
        currentSession: sessionId,
        messages: data.messages,
      }));
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await apiService.deleteChatSession(sessionId);
      setState(prev => {
        const newSessions = prev.sessions.filter(s => s.id !== sessionId);
        const needsNewSession = prev.currentSession === sessionId;
        
        return {
          ...prev,
          sessions: newSessions,
          currentSession: needsNewSession ? (newSessions[0]?.id || null) : prev.currentSession,
          messages: needsNewSession ? [] : prev.messages,
        };
      });

      // If we deleted the current session and there are other sessions, load the first one
      if (state.currentSession === sessionId && state.sessions.length > 1) {
        const remainingSessions = state.sessions.filter(s => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          await loadSession(remainingSessions[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const sendMessage = async (content: string) => {
    if (!state.currentSession || !state.systemReady) {
      console.error('No active session or system not ready');
      return;
    }

    try {
      const response = await apiService.sendMessage(state.currentSession, content);
      
      // Update messages with both user and AI messages
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, response.user_message, response.ai_message],
        sessions: prev.sessions.map(s => 
          s.id === response.session.id ? response.session : s
        ),
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
      // You might want to show an error message to the user here
    }
  };

  const toggleSidebar = () => {
    setState(prev => ({ ...prev, sidebarOpen: !prev.sidebarOpen }));
  };

  if (state.loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        isOpen={state.sidebarOpen}
        sessions={state.sessions}
        currentSession={state.currentSession}
        onSessionSelect={loadSession}
        onSessionDelete={deleteSession}
        onNewSession={createNewSession}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className="md:hidden"
              >
                {state.sidebarOpen ? <X size={20} /> : <Menu size={20} />}
              </Button>
              <h1 className="font-semibold text-lg">Edify AI Chatbot</h1>
              {!state.systemReady && (
                <span className="text-sm text-destructive">System Not Ready</span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant={activeTab === 'chat' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('chat')}
                className="hidden md:flex"
              >
                <MessageSquare size={16} className="mr-2" />
                Chat
              </Button>
              <Button
                variant={activeTab === 'upload' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('upload')}
                className="hidden md:flex"
              >
                <Upload size={16} className="mr-2" />
                Upload
              </Button>
              <Button
                variant={activeTab === 'status' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('status')}
                className="hidden md:flex"
              >
                <Info size={16} className="mr-2" />
                Status
              </Button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && (
            <div className="h-full">
              {state.currentSession ? (
                <AssistantThread
                  messages={state.messages}
                  onSendMessage={sendMessage}
                  disabled={!state.systemReady}
                />
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <MessageSquare size={48} className="mx-auto mb-4 text-muted-foreground" />
                    <h3 className="text-lg font-semibold mb-2">No Active Chat</h3>
                    <p className="text-muted-foreground mb-4">
                      Create a new chat to get started
                    </p>
                    <Button onClick={() => createNewSession()}>
                      Start New Chat
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'upload' && (
            <div className="p-6">
              <FileUpload onUploadComplete={initializeApp} />
            </div>
          )}

          {activeTab === 'status' && (
            <div className="p-6">
              <SystemStatus />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Custom Assistant Thread component
interface AssistantThreadProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

function AssistantThread({ messages, onSendMessage, disabled }: AssistantThreadProps) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    const content = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      await onSendMessage(content);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground ml-4'
                  : 'bg-muted mr-4'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              {message.metadata?.sources && message.metadata.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/50">
                  <p className="text-xs text-muted-foreground">
                    Sources: {message.metadata.sources.join(', ')}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg p-3 mr-4">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={disabled ? "System not ready..." : "Type your message..."}
            disabled={disabled || isLoading}
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading || disabled}
          >
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}

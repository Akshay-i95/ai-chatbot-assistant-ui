import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Download, Copy, Check, Menu, MessageSquare, Info } from 'lucide-react';
import { apiService, type ChatSession, type ChatMessage } from '../lib/api';

interface Source {
  filename: string;
  total_pages?: number;
  download_url?: string;
}

interface ModernMessage extends ChatMessage {
  metadata?: {
    sources?: Source[];
    processing_time?: number;
    model_used?: string;
  };
}

export function ModernChatInterface() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<ModernMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [systemReady, setSystemReady] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeApp = async () => {
    try {
      // Check system health
      const health = await apiService.healthCheck();
      setSystemReady(health.system_ready);

      // Load chat sessions
      const sessionsData = await apiService.getChatSessions();
      setSessions(sessionsData);

      // Create new session if none exist
      if (sessionsData.length === 0) {
        await handleNewChat();
      } else {
        // Load the most recent session
        setCurrentSession(sessionsData[0].id);
        await loadSession(sessionsData[0].id);
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      const sessionData = await apiService.getChatSession(sessionId);
      setMessages(sessionData.messages || []);
      setCurrentSession(sessionId);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const handleNewChat = async () => {
    try {
      const newSession = await apiService.createChatSession();
      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create new chat:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentSession || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await apiService.sendMessage(currentSession, userMessage);
      
      // Update messages with both user and AI messages
      setMessages(prev => [
        ...prev,
        response.user_message,
        response.ai_message
      ]);

      // Update sessions list
      setSessions(prev => 
        prev.map(session => 
          session.id === currentSession 
            ? { ...session, title: response.session.title, updated_at: response.session.updated_at }
            : session
        )
      );
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const downloadFile = async (filename: string) => {
    try {
      const response = await fetch(`/api/files/download/${filename}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatMarkdown = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
          h1: ({ children }) => <h1 className="text-xl font-bold mb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-bold mb-2">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{children}</code>,
          pre: ({ children }) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto text-sm">{children}</pre>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <div className="chat-container">
      {/* Sidebar */}
      <div className={`sidebar ${!sidebarOpen ? 'closed' : ''}`}>
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={handleNewChat}
            className="btn-primary w-full"
          >
            <MessageSquare className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  session.id === currentSession
                    ? 'bg-black text-white'
                    : 'hover:bg-gray-100'
                }`}
              >
                <div className="font-medium truncate">{session.title}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(session.updated_at).toLocaleDateString()}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-200">
          <div className={`flex items-center gap-2 text-sm ${
            systemReady ? 'text-green-600' : 'text-red-600'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              systemReady ? 'bg-green-500' : 'bg-red-500'
            }`} />
            {systemReady ? 'System Ready' : 'System Not Ready'}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-chat">
        {/* Header */}
        <div className="chat-header">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="btn-ghost lg:hidden"
              >
                <Menu className="w-5 h-5" />
              </button>
              <h1 className="text-lg font-semibold">Edify AI Chatbot</h1>
            </div>
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">
                {messages.length} messages
              </span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Start a conversation
                </h3>
                <p className="text-gray-500">
                  Ask me anything about your documents and I'll help you find answers.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-0">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-bubble message-animation ${
                    message.role === 'user' ? 'user-message' : 'assistant-message'
                  }`}
                >
                  <div className="flex gap-4">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${
                      message.role === 'user' ? 'bg-black' : 'bg-gray-600'
                    }`}>
                      {message.role === 'user' ? 'U' : 'AI'}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className={`message-content ${
                        message.role === 'user' ? 'user-content' : 'assistant-content'
                      }`}>
                        {message.role === 'user' ? (
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        ) : (
                          formatMarkdown(message.content)
                        )}
                      </div>

                      {/* Message Actions */}
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={() => copyToClipboard(message.content, message.id)}
                          className="btn-ghost"
                          title="Copy message"
                        >
                          {copiedMessageId === message.id ? (
                            <Check className="w-4 h-4 text-green-600" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                        
                        <span className="text-xs text-gray-500">
                          {new Date(message.created_at).toLocaleTimeString()}
                        </span>
                      </div>

                      {/* Sources */}
                      {message.metadata?.sources && message.metadata.sources.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Sources:</h4>
                          <div className="grid gap-2">
                            {message.metadata.sources.map((source, idx) => (
                              <div key={idx} className="source-card">
                                <div className="flex items-center justify-between">
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 truncate">
                                      {source.filename}
                                    </p>
                                    {source.total_pages && (
                                      <p className="text-xs text-gray-500">
                                        {source.total_pages} pages
                                      </p>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => downloadFile(source.filename)}
                                    className="btn-ghost"
                                    title="Download PDF"
                                  >
                                    <Download className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="message-bubble assistant-message">
                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-sm font-medium">
                      AI
                    </div>
                    <div className="flex-1">
                      <div className="typing-indicator text-gray-500">
                        Thinking...
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="chat-input-container">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your documents..."
                className="chat-input"
                rows={1}
                disabled={!systemReady}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading || !systemReady}
                className="btn-primary"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            
            {!systemReady && (
              <p className="text-sm text-red-600 mt-2 text-center">
                System is not ready. Please wait for initialization to complete.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

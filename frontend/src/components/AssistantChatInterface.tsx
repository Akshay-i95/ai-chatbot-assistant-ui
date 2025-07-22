import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Download, Copy, Check, Menu, MessageSquare, Brain, FileText, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { apiService, type ChatSession, type ChatMessage } from '../lib/api';

interface EnhancedMessage extends ChatMessage {
  metadata?: {
    sources?: any[];
    processing_time?: number;
    model_used?: string;
    reasoning?: string;
    confidence?: number;
  };
}

interface ChatState {
  sessions: ChatSession[];
  currentSession: string | null;
  messages: EnhancedMessage[];
  inputValue: string;
  isLoading: boolean;
  sidebarOpen: boolean;
  systemReady: boolean;
  copiedMessageId: string | null;
  showReasoning: { [key: string]: boolean };
  showSources: { [key: string]: boolean };
  typingStage: 'reasoning' | 'response' | 'sources' | null;
  animatingReasoning: string | null;
}

export function AssistantChatInterface() {
  const [state, setState] = useState<ChatState>({
    sessions: [],
    currentSession: null,
    messages: [],
    inputValue: '',
    isLoading: false,
    sidebarOpen: true,
    systemReady: false,
    copiedMessageId: null,
    showReasoning: {},
    showSources: {},
    typingStage: null,
    animatingReasoning: null,
  });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [state.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const setState2 = (updates: Partial<ChatState>) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  const initializeApp = async () => {
    try {
      const health = await apiService.healthCheck();
      setState2({ systemReady: health.system_ready });

      const sessionsData = await apiService.getChatSessions();
      setState2({ sessions: sessionsData });

      if (sessionsData.length === 0) {
        await handleNewChat();
      } else {
        setState2({ currentSession: sessionsData[0].id });
        await loadSession(sessionsData[0].id);
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      const sessionData = await apiService.getChatSession(sessionId);
      setState2({ 
        messages: sessionData.messages || [],
        currentSession: sessionId 
      });
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const handleNewChat = async () => {
    try {
      const newSession = await apiService.createChatSession();
      setState2({ 
        sessions: [newSession, ...state.sessions],
        currentSession: newSession.id,
        messages: []
      });
    } catch (error) {
      console.error('Failed to create new chat:', error);
    }
  };

  const simulateTypingFlow = async (userMessage: string, tempMessageId: string): Promise<any> => {
    if (!state.currentSession) return;

    // Stage 1: Show reasoning animation
    setState2({ 
      typingStage: 'reasoning', 
      animatingReasoning: tempMessageId,
      showReasoning: { ...state.showReasoning, [tempMessageId]: true }
    });
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Stage 2: Show response generation
    setState2({ typingStage: 'response' });
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Make actual API call
    const response = await apiService.sendMessage(state.currentSession, userMessage);

    // Stage 3: Show sources briefly
    setState2({ typingStage: 'sources' });
    await new Promise(resolve => setTimeout(resolve, 800));

    // Close reasoning after response is complete
    setState2({ 
      typingStage: null, 
      animatingReasoning: null,
      showReasoning: { ...state.showReasoning, [tempMessageId]: false, [response.ai_message.id]: false }
    });

    return response;
  };

  const handleSendMessage = async () => {
    if (!state.inputValue.trim() || !state.currentSession || state.isLoading) return;

    const userMessage = state.inputValue.trim();
    const tempMessageId = 'temp-' + Date.now();
    
    setState2({ inputValue: '', isLoading: true });

    try {
      const response = await simulateTypingFlow(userMessage, tempMessageId);
      
      setState2({
        messages: [...state.messages, response.user_message, response.ai_message],
        sessions: state.sessions.map(session => 
          session.id === state.currentSession 
            ? { ...session, title: response.session.title, updated_at: response.session.updated_at }
            : session
        )
      });
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setState2({ isLoading: false });
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
      setState2({ copiedMessageId: messageId });
      setTimeout(() => setState2({ copiedMessageId: null }), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const downloadFile = async (filename: string) => {
    try {
      const response = await fetch(`http://localhost:5000/api/files/download/${encodeURIComponent(filename)}`);
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
      } else {
        console.error('Download failed:', response.statusText);
        alert('Download failed. Please try again.');
      }
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please check your connection.');
    }
  };

  const toggleReasoning = (messageId: string) => {
    setState2({
      showReasoning: {
        ...state.showReasoning,
        [messageId]: !state.showReasoning[messageId]
      }
    });
  };

  const toggleSources = (messageId: string) => {
    setState2({
      showSources: {
        ...state.showSources,
        [messageId]: !state.showSources[messageId]
      }
    });
  };

  const formatMarkdown = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-3 leading-7">{children}</p>,
          h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 text-gray-900">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold mb-3 text-gray-800">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 text-gray-700">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-2 ml-4">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-2 ml-4">{children}</ol>,
          li: ({ children }) => <li className="leading-7">{children}</li>,
          code: ({ children }) => <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">{children}</code>,
          pre: ({ children }) => <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono mb-3">{children}</pre>,
          strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-700 mb-3">{children}</blockquote>,
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  const TypingIndicator = ({ stage }: { stage: 'reasoning' | 'response' | 'sources' }) => {
    const stages = {
      reasoning: { icon: Brain, text: 'Analyzing your question...', color: 'text-blue-600' },
      response: { icon: MessageSquare, text: 'Generating response...', color: 'text-green-600' },
      sources: { icon: FileText, text: 'Finding sources...', color: 'text-purple-600' }
    };

    const { icon: Icon, text, color } = stages[stage];

    return (
      <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg animate-pulse">
        <Icon className={`w-5 h-5 ${color} animate-bounce`} />
        <span className="text-gray-700">{text}</span>
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Sidebar */}
      <div className={`w-80 bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
        !state.sidebarOpen ? '-ml-80' : ''
      }`}>
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={handleNewChat}
            className="w-full bg-black text-white px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 font-medium"
          >
            <MessageSquare className="w-5 h-5" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {state.sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`w-full text-left p-4 rounded-lg transition-all duration-200 group ${
                  session.id === state.currentSession
                    ? 'bg-black text-white shadow-lg'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <div className="font-medium truncate text-sm">{session.title}</div>
                <div className={`text-xs mt-1 ${
                  session.id === state.currentSession ? 'text-gray-300' : 'text-gray-500'
                }`}>
                  {new Date(session.updated_at).toLocaleDateString()}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-200">
          <div className={`flex items-center gap-3 text-sm ${
            state.systemReady ? 'text-green-600' : 'text-red-600'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              state.systemReady ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="font-medium">
              {state.systemReady ? 'System Ready' : 'System Not Ready'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setState2({ sidebarOpen: !state.sidebarOpen })}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Menu className="w-5 h-5 text-gray-600" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Edify AI Assistant</h1>
                <p className="text-sm text-gray-500">Advanced AI with reasoning capabilities</p>
              </div>
            </div>
            <div className="text-sm text-gray-500">
              {state.messages.length} messages
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {state.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 bg-black rounded-full flex items-center justify-center mx-auto mb-6">
                  <MessageSquare className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-2xl font-semibold text-gray-900 mb-3">
                  Start a conversation
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  Ask me anything about your documents. I'll analyze your question, 
                  provide detailed reasoning, and cite relevant sources.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6 p-6">
              {state.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-5 h-5 text-white" />
                    </div>
                  )}
                  
                  <div className={`max-w-4xl ${message.role === 'user' ? 'order-first' : ''}`}>
                    {message.role === 'user' ? (
                      <div className="bg-gray-900 text-white px-6 py-4 rounded-2xl">
                        <p className="leading-relaxed">{message.content}</p>
                      </div>
                    ) : (
                      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
                        {/* Reasoning Section - with animation */}
                        {message.metadata?.reasoning && (
                          <div className="border-b border-gray-100">
                            <button
                              onClick={() => toggleReasoning(message.id)}
                              className="w-full p-4 text-left hover:bg-gray-50 transition-colors flex items-center justify-between"
                            >
                              <div className="flex items-center gap-3">
                                <Brain className={`w-5 h-5 text-blue-600 ${
                                  state.animatingReasoning === message.id ? 'animate-pulse' : ''
                                }`} />
                                <span className="font-medium text-gray-900">Reasoning Process</span>
                                {state.animatingReasoning === message.id && (
                                  <div className="flex gap-1 ml-2">
                                    <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                  </div>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="text-xs text-gray-500">
                                  {state.showReasoning[message.id] ? 'Hide' : 'Show'}
                                </div>
                                {state.showReasoning[message.id] ? (
                                  <ChevronUp className="w-4 h-4 text-gray-500" />
                                ) : (
                                  <ChevronDown className="w-4 h-4 text-gray-500" />
                                )}
                              </div>
                            </button>
                            {state.showReasoning[message.id] && (
                              <div className="px-4 pb-4 animate-in slide-in-from-top duration-300">
                                <div className="bg-blue-50 p-4 rounded-lg">
                                  <div className="text-gray-700 leading-relaxed">
                                    {formatMarkdown(message.metadata.reasoning)}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Main Response */}
                        <div className="p-6">
                          <div className="prose prose-gray max-w-none">
                            {formatMarkdown(message.content)}
                          </div>
                          
                          {/* Message Actions */}
                          <div className="flex items-center gap-3 mt-6 pt-4 border-t border-gray-100">
                            <button
                              onClick={() => copyToClipboard(message.content, message.id)}
                              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                              {state.copiedMessageId === message.id ? (
                                <>
                                  <Check className="w-4 h-4 text-green-600" />
                                  <span className="text-green-600">Copied!</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-4 h-4" />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                            
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              <span>{new Date(message.created_at).toLocaleTimeString()}</span>
                              {message.metadata?.model_used && (
                                <>
                                  <span>•</span>
                                  <span>{message.metadata.model_used}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Sources - Initially Closed */}
                        {message.metadata?.sources && message.metadata.sources.length > 0 && (
                          <div className="border-t border-gray-100 bg-gray-50">
                            <button
                              onClick={() => toggleSources(message.id)}
                              className="w-full p-4 text-left hover:bg-gray-100 transition-colors flex items-center justify-between"
                            >
                              <div className="flex items-center gap-3">
                                <FileText className="w-5 h-5 text-purple-600" />
                                <h4 className="font-medium text-gray-900">
                                  Sources ({message.metadata.sources.length})
                                </h4>
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="text-xs text-gray-500">
                                  {state.showSources[message.id] ? 'Hide' : 'Show'}
                                </div>
                                {state.showSources[message.id] ? (
                                  <ChevronUp className="w-4 h-4 text-gray-500" />
                                ) : (
                                  <ChevronDown className="w-4 h-4 text-gray-500" />
                                )}
                              </div>
                            </button>
                            
                            {state.showSources[message.id] && (
                              <div className="px-4 pb-4 animate-in slide-in-from-top duration-300">
                                <div className="grid gap-3">
                                  {message.metadata.sources.map((source, idx) => (
                                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                      <div className="flex items-center justify-between">
                                        <div className="flex-1 min-w-0">
                                          <p className="font-medium text-gray-900 truncate text-sm">
                                            {source.filename}
                                          </p>
                                          <div className="flex items-center gap-4 mt-1 text-xs text-gray-600">
                                            {source.total_pages && (
                                              <span>{source.total_pages} pages</span>
                                            )}
                                            {source.relevance_score && (
                                              <span>Relevance: {(source.relevance_score * 100).toFixed(0)}%</span>
                                            )}
                                          </div>
                                        </div>
                                        <button
                                          onClick={() => downloadFile(source.filename)}
                                          className="ml-3 flex items-center gap-2 px-3 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm"
                                        >
                                          <Download className="w-4 h-4" />
                                          Download
                                        </button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {message.role === 'user' && (
                    <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-white font-medium text-sm">U</span>
                    </div>
                  )}
                </div>
              ))}
              
              {/* Typing Indicators */}
              {state.isLoading && state.typingStage && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                    <MessageSquare className="w-5 h-5 text-white" />
                  </div>
                  <div className="max-w-4xl">
                    <TypingIndicator stage={state.typingStage} />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-200 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-4">
              <textarea
                ref={inputRef}
                value={state.inputValue}
                onChange={(e) => setState2({ inputValue: e.target.value })}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your documents..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent resize-none text-gray-900 placeholder-gray-500"
                rows={1}
                disabled={!state.systemReady || state.isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={!state.inputValue.trim() || state.isLoading || !state.systemReady}
                className="px-6 py-3 bg-black text-white rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2"
              >
                {state.isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            
            {!state.systemReady && (
              <p className="text-sm text-red-600 mt-3 text-center">
                System is initializing. Please wait...
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
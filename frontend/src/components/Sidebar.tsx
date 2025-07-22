import React from 'react';
import { type ChatSession } from '../lib/api';
import { Button } from './ui/button';
import { 
  MessageSquare, 
  Upload, 
  Info, 
  Plus, 
  Trash2, 
  Calendar 
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  sessions: ChatSession[];
  currentSession: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionDelete: (sessionId: string) => void;
  onNewSession: () => void;
  activeTab: 'chat' | 'upload' | 'status';
  onTabChange: (tab: 'chat' | 'upload' | 'status') => void;
}

export function Sidebar({
  isOpen,
  sessions,
  currentSession,
  onSessionSelect,
  onSessionDelete,
  onNewSession,
  activeTab,
  onTabChange,
}: SidebarProps) {
  if (!isOpen) return null;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="w-80 border-r bg-card h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <Button 
          onClick={onNewSession}
          className="w-full justify-start"
          variant="outline"
        >
          <Plus size={16} className="mr-2" />
          New Chat
        </Button>
      </div>

      {/* Navigation Tabs */}
      <div className="p-2 border-b">
        <div className="flex flex-col gap-1">
          <Button
            variant={activeTab === 'chat' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onTabChange('chat')}
            className="justify-start"
          >
            <MessageSquare size={16} className="mr-2" />
            Chat
          </Button>
          <Button
            variant={activeTab === 'upload' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onTabChange('upload')}
            className="justify-start"
          >
            <Upload size={16} className="mr-2" />
            Upload Files
          </Button>
          <Button
            variant={activeTab === 'status' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onTabChange('status')}
            className="justify-start"
          >
            <Info size={16} className="mr-2" />
            System Status
          </Button>
        </div>
      </div>

      {/* Chat Sessions */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group relative rounded-lg p-3 cursor-pointer transition-colors ${
                currentSession === session.id
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent hover:text-accent-foreground'
              }`}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm truncate">
                    {session.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Calendar size={12} className="opacity-60" />
                    <span className="text-xs opacity-60">
                      {formatDate(session.updated_at)}
                    </span>
                    <span className="text-xs opacity-60">
                      {session.message_count} messages
                    </span>
                  </div>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className={`h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity ${
                    currentSession === session.id 
                      ? 'text-primary-foreground hover:bg-primary-foreground/20' 
                      : 'hover:bg-destructive hover:text-destructive-foreground'
                  }`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSessionDelete(session.id);
                  }}
                >
                  <Trash2 size={12} />
                </Button>
              </div>
            </div>
          ))}
        </div>
        
        {sessions.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-8">
            No chat sessions yet.
            <br />
            Start a new conversation!
          </div>
        )}
      </div>
    </div>
  );
}

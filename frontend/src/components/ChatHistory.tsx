import React from 'react';
import { type ChatSession, type ChatMessage } from '../lib/api';
import { Calendar, MessageSquare } from 'lucide-react';

interface ChatHistoryProps {
  sessions: ChatSession[];
  currentSession: string | null;
  onSessionSelect: (sessionId: string) => void;
}

export function ChatHistory({ sessions, currentSession, onSessionSelect }: ChatHistoryProps) {
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
    <div className="space-y-2">
      {sessions.map((session) => (
        <div
          key={session.id}
          className={`p-3 rounded-lg cursor-pointer transition-colors ${
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
                <MessageSquare size={12} className="opacity-60" />
                <span className="text-xs opacity-60">
                  {session.message_count}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
      
      {sessions.length === 0 && (
        <div className="text-center text-muted-foreground text-sm py-4">
          No chat history yet
        </div>
      )}
    </div>
  );
}

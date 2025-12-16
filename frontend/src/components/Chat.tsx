import React, { useState, useRef, useEffect } from 'react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { Wrench, Trash2, LogOut, Menu, X, Plus } from 'lucide-react';
import { apiService, type Message as MessageType } from '../services/api';

interface ChatSession {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  message_count: number;
}

interface ChatProps {
  onLogout: () => void;
}

export const Chat: React.FC<ChatProps> = ({ onLogout }) => {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  useEffect(() => {
    // Load sessions on mount
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await apiService.getSessions();
      setSessions(response.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: MessageType = {
      role: 'user',
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setStreamingMessage('');

    try {
      // Stream the response
      let fullResponse = '';
      let receivedThreadId: string | undefined;

      for await (const chunk of apiService.streamMessage(content, currentThreadId || undefined)) {
        if (chunk.threadId) {
          receivedThreadId = chunk.threadId;
        } else if (chunk.content) {
          fullResponse += chunk.content;
          setStreamingMessage(fullResponse);
        }
      }

      // Add complete assistant message
      const assistantMessage: MessageType = {
        role: 'assistant',
        content: fullResponse,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setStreamingMessage('');

      // Set thread_id if this was a new chat
      if (receivedThreadId && !currentThreadId) {
        setCurrentThreadId(receivedThreadId);
      }
      
      const effectiveThreadId = receivedThreadId || currentThreadId;

      // Update sessions immediately - add current conversation to top
      const firstUserMsg = userMessage.content;
      const title = firstUserMsg.slice(0, 50) + (firstUserMsg.length > 50 ? '...' : '');
      const preview = fullResponse.slice(0, 60) + (fullResponse.length > 60 ? '...' : '');
      
      if (effectiveThreadId) {
        const newSession: ChatSession = {
          id: effectiveThreadId,
          title,
          preview,
          timestamp: new Date().toISOString(),
          message_count: messages.length + 2, // +2 for user message and assistant response
        };

        // Add to top of sessions list, remove if already exists
        setSessions((prev) => {
          const filtered = prev.filter(s => s.id !== newSession.id);
          return [newSession, ...filtered];
        });
      }

      // Reload full sessions from backend to sync
      await loadSessions();
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const msg = String(error?.message || 'Unknown error');
      if (msg.includes('HTTP 401')) {
        // Token likely expired; force logout so user can login again
        const authError: MessageType = {
          role: 'assistant',
          content: 'Your session expired. Please log in again.',
        };
        setMessages((prev) => [...prev, authError]);
      } else {
        const errorMessage: MessageType = {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
      setStreamingMessage('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (confirm('Are you sure you want to clear all conversations?')) {
      try {
        await apiService.clearChatHistory();
        setMessages([]);
        setSessions([]);
        setCurrentThreadId(null);
      } catch (error) {
        console.error('Failed to clear history:', error);
      }
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setStreamingMessage('');
    setCurrentThreadId(null);
  };

  const handleSessionClick = async (sessionId: string) => {
    if (sessionId === currentThreadId) return; // Already viewing this session
    
    try {
      setIsLoading(true);
      const history = await apiService.getChatHistory(sessionId);
      setMessages(history);
      setCurrentThreadId(sessionId);
      setStreamingMessage('');
    } catch (error) {
      console.error('Failed to load session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-chat-bg">
      {/* Sidebar - Always visible */}
      <div
        className={`bg-chat-sidebar border-r border-chat-border transition-all duration-300 flex flex-col ${
          sidebarOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
      >
          {/* Sidebar Header */}
          <div className="p-3 border-b border-chat-border">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2 bg-chat-input hover:bg-chat-hover rounded-lg transition-colors text-chat-text"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm font-medium">New chat</span>
            </button>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-2 py-2">
            {sessions.length > 0 && (
              <>
                <div className="text-xs font-semibold text-chat-text-secondary px-3 py-2">
                  Your chats
                </div>
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => handleSessionClick(session.id)}
                    disabled={isLoading}
                    className={`w-full text-left px-3 py-3 hover:bg-chat-hover rounded-lg transition-colors group mb-1 ${
                      currentThreadId === session.id ? 'bg-chat-hover' : ''
                    } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <div className="text-sm text-chat-text truncate font-medium mb-1">
                      {session.title}
                    </div>
                    <div className="text-xs text-chat-text-secondary truncate">
                      {session.preview}
                    </div>
                  </button>
                ))}
              </>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="border-t border-chat-border p-2">
            <button
              onClick={handleClearHistory}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-chat-hover rounded-lg transition-colors text-chat-text-secondary text-sm"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear conversations</span>
            </button>
            <button
              onClick={onLogout}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-chat-hover rounded-lg transition-colors text-chat-text-secondary text-sm"
            >
              <LogOut className="w-4 h-4" />
              <span>Log out</span>
            </button>
          </div>
        </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header - Always visible */}
        <div className="border-b border-chat-border bg-chat-bg px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-chat-hover rounded-lg transition-colors"
              >
                {sidebarOpen ? (
                  <X className="w-5 h-5 text-chat-text-secondary" />
                ) : (
                  <Menu className="w-5 h-5 text-chat-text-secondary" />
                )}
              </button>
              <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                <Wrench className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-lg font-semibold text-white">Repair Assistant</h1>
            </div>
          </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {messages.length === 0 && !streamingMessage && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md px-4">
                <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Wrench className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  How can I help you fix something today?
                </h2>
                <p className="text-chat-text-secondary">
                  Ask me about device repairs, troubleshooting, or get step-by-step repair guides.
                </p>
                <div className="mt-8 grid gap-3">
                  <button
                    onClick={() => handleSendMessage('How do I fix my iPhone 13 screen?')}
                    className="p-4 bg-chat-input hover:bg-chat-user rounded-lg text-left transition-colors"
                  >
                    <p className="text-chat-text text-sm">
                      How do I fix my iPhone 13 screen?
                    </p>
                  </button>
                  <button
                    onClick={() => handleSendMessage('My PS5 disc drive is not working')}
                    className="p-4 bg-chat-input hover:bg-chat-user rounded-lg text-left transition-colors"
                  >
                    <p className="text-chat-text text-sm">
                      My PS5 disc drive is not working
                    </p>
                  </button>
                  <button
                    onClick={() => handleSendMessage('Laptop battery replacement guide')}
                    className="p-4 bg-chat-input hover:bg-chat-user rounded-lg text-left transition-colors"
                  >
                    <p className="text-chat-text text-sm">
                      Laptop battery replacement guide
                    </p>
                  </button>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <Message
              key={index}
              role={message.role}
              content={message.content}
            />
          ))}

          {streamingMessage && (
            <Message
              role="assistant"
              content={streamingMessage}
              isStreaming={true}
            />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
};

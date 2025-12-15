import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import { cn } from '../lib/utils';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

export const Message: React.FC<MessageProps> = ({ role, content, isStreaming }) => {
  const isUser = role === 'user';

  return (
    <div
      className={cn(
        'w-full border-b border-chat-border',
        isUser ? 'bg-chat-user' : 'bg-chat-assistant'
      )}
    >
      <div className="max-w-3xl mx-auto px-4 py-6 flex gap-6">
        {/* Avatar */}
        <div
          className={cn(
            'w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0',
            isUser ? 'bg-purple-600' : 'bg-green-600'
          )}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <div className="prose prose-invert max-w-none">
            {isUser ? (
              <p className="text-chat-text whitespace-pre-wrap">{content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Headings
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold text-chat-text mt-4 mb-2">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-bold text-chat-text mt-3 mb-2">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-semibold text-chat-text mt-2 mb-1">
                      {children}
                    </h3>
                  ),
                  
                  // Paragraphs
                  p: ({ children }) => (
                    <p className="text-chat-text mb-4 leading-7">
                      {children}
                    </p>
                  ),

                  // Lists
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside text-chat-text mb-4 space-y-1">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside text-chat-text mb-4 space-y-1">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-chat-text leading-7">{children}</li>
                  ),

                  // Code
                  code: ({ inline, children, ...props }: any) =>
                    inline ? (
                      <code
                        className="bg-chat-input text-chat-text px-1.5 py-0.5 rounded text-sm font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className="block bg-chat-input text-chat-text p-4 rounded-lg text-sm font-mono overflow-x-auto mb-4"
                        {...props}
                      >
                        {children}
                      </code>
                    ),

                  // Links
                  a: ({ children, href }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline"
                    >
                      {children}
                    </a>
                  ),

                  // Strong/Bold
                  strong: ({ children }) => (
                    <strong className="font-bold text-white">{children}</strong>
                  ),

                  // Emphasis/Italic
                  em: ({ children }) => (
                    <em className="italic text-chat-text-secondary">{children}</em>
                  ),

                  // Blockquote
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-chat-border pl-4 my-4 text-chat-text-secondary italic">
                      {children}
                    </blockquote>
                  ),

                  // Horizontal Rule
                  hr: () => <hr className="border-chat-border my-4" />,

                  // Images
                  img: ({ src, alt }) => (
                    <img
                      src={src}
                      alt={alt}
                      className="max-w-full h-auto rounded-lg my-4"
                    />
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            )}

            {/* Streaming cursor */}
            {isStreaming && (
              <span className="inline-block w-2 h-5 bg-white ml-1 animate-pulse" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

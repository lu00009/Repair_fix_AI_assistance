import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import { cn } from '../lib/utils.ts';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  stepImage?: string | null;
  stepImages?: Array<{ step: number; url: string }> | null;
}

export const Message: React.FC<MessageProps> = ({ role, content, isStreaming, stepImage, stepImages }) => {
  const isUser = role === 'user';

  // If stepImages array is provided, use it for progressive rendering
  // Otherwise fall back to extracting from content
  let extractedStepImage: string | null = null;
  if (stepImage) {
    extractedStepImage = stepImage;
  } else if (!stepImages && typeof content === 'string') {
    try {
      // Match images like ![Step 1 image](https://...)
      const stepMatch = content.match(/!\[\s*Step\s*\d+[^\]]*\]\((https?:\/\/[^)]+)\)/i);
      if (stepMatch && stepMatch[1]) {
        extractedStepImage = stepMatch[1];
      } else {
        // Fallback: any markdown image
        const anyMatch = content.match(/!\[[^\]]*\]\((https?:\/\/[^)]+)\)/i);
        if (anyMatch && anyMatch[1]) extractedStepImage = anyMatch[1];
      }
    } catch (e) {
      extractedStepImage = null;
    }
  }

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
                  h3: ({ children }) => {
                    // Check if this is a step heading to inject step image
                    const childText = String(children);
                    const stepMatch = childText.match(/Step\s+(\d+)/i);

                    return (
                      <>
                        <h3 className="text-lg font-semibold text-chat-text mt-2 mb-1">
                          {children}
                        </h3>
                        {/* Render step image right after step heading if available */}
                        {stepMatch && stepImages && stepImages.length > 0 && (
                          (() => {
                            const stepNum = parseInt(stepMatch[1]);
                            const stepImg = stepImages.find(img => img.step === stepNum);
                            return stepImg ? (
                              <img
                                src={stepImg.url}
                                alt={`Step ${stepNum} image`}
                                className="max-w-full h-auto rounded-lg my-4"
                              />
                            ) : null;
                          })()
                        )}
                      </>
                    );
                  },

                  // Paragraphs
                  p: ({ children }) => {
                    const text = String(children);
                    const stepMatch = text.match(/\bStep\s*(\d+)\b[:]?/i);
                    return (
                      <>
                        <p className="text-chat-text mb-4 leading-7">{children}</p>
                        {stepMatch && stepImages && stepImages.length > 0 && (
                          (() => {
                            const stepNum = parseInt(stepMatch[1]);
                            const imgs = stepImages.filter(img => img.step === stepNum);
                            return imgs.length > 0 ? (
                              <div>
                                {imgs.map(img => (
                                  <img key={img.url} src={img.url} alt={`Step ${stepNum} image`} className="max-w-full h-auto rounded-lg my-4" />
                                ))}
                              </div>
                            ) : null;
                          })()
                        )}
                      </>
                    );
                  },

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

                  // Images - hide if we're using stepImages (to avoid duplication)
                  img: ({ src, alt }) => {
                    // If stepImages is provided, hide step images from markdown (they're rendered via h3)
                    if (stepImages && alt?.match(/Step\s+\d+/i)) {
                      return null;
                    }
                    return (
                      <img
                        src={src}
                        alt={alt}
                        className="max-w-full h-auto rounded-lg my-4"
                      />
                    );
                  },
                }}
              >
                {content}
              </ReactMarkdown>
            )}

            {/* Render first-step image (if provided and no stepImages array) - fallback for legacy messages */}
            {!isUser && !stepImages && extractedStepImage && (
              <div>
                <img src={extractedStepImage} alt="step" className="max-w-full h-auto rounded-lg my-4" />
              </div>
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

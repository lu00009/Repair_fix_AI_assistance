// Clean single-file ApiService implementation
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  step_image?: string | null;
  step_images?: Array<{ step: number; url: string }> | null;
}

export interface StreamChunk {
  content?: string; // token or text chunk
  threadId?: string;
  stepImage?: string; // a URL for a step image (may be on done or progressive)
  stepNumber?: number; // when progressive image is emitted
  stepImages?: Array<{ step: number; url: string }>;
}

export class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  setToken(token: string, refreshToken?: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
  }

  // --- Auth helpers ---
  async login(credentials: { email: string; password: string }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const txt = await response.text().catch(() => '');
      throw new Error(`Login failed: ${response.status} ${txt}`);
    }

    const data = await response.json();
    if (data?.access_token) {
      this.setToken(data.access_token, data.refresh_token);
    }
    return data;
  }

  async signup(credentials: { email: string; password: string }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const txt = await response.text().catch(() => '');
      throw new Error(`Signup failed: ${response.status} ${txt}`);
    }

    return await response.json();
  }

  private getAuthHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    return headers;
  }

  // Stream a chat message to the server. Returns an async generator yielding StreamChunk objects.
  async *streamMessage(message: string, threadId?: string): AsyncGenerator<StreamChunk, void, unknown> {
    const body = JSON.stringify({ message, thread_id: threadId });
    const res = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body,
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
    }

    if (!res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events separated by double-newline
      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);

        if (!raw) continue;

        // Combine multiple 'data:' lines if present
        const lines = raw.split(/\r?\n/).filter(Boolean);
        const dataLines = lines.filter((l) => l.startsWith('data:'));
        if (dataLines.length === 0) continue;

        // Join all data: payloads (strip leading 'data:')
        const payload = dataLines.map((l) => l.replace(/^data:\s?/, '')).join('\n');

        if (!payload || payload === '[DONE]') continue;

        let parsed: any = null;
        try {
          parsed = JSON.parse(payload);
        } catch (err) {
          // Log and continue on parse error
          console.error('Failed to parse SSE data:', payload, err);
          continue;
        }

        // Handle known event shapes
        if (parsed.type === 'step_image') {
          yield { stepImage: parsed.url, stepNumber: parsed.step };
        } else if (parsed.type === 'word') {
          // word-by-word streaming event
          const c = parsed.content;
          if (c) yield { content: String(c) };
        } else if (parsed.type === 'status') {
          // status messages can be treated as content
          yield { content: parsed.content };
        } else if (parsed.type === 'line') {
          // line-by-line streaming
          const c = parsed.content;
          if (c) yield { content: String(c) };
        } else if (parsed.type === 'token' || parsed.type === 'text' || parsed.type === 'chunk') {
          // streaming token (fallback for backward compatibility)
          const c = parsed.content || parsed.token || parsed.text || parsed.chunk;
          if (c) yield { content: String(c) };
        } else if (parsed.type === 'done' || parsed.thread_id) {
          // final payload
          const finalText = (parsed.message || (parsed.structured && parsed.structured.text)) || '';
          const thread_id = parsed.thread_id || parsed.threadId || parsed.thread;
          const stepImage = parsed.step_image || (parsed.structured && parsed.structured.step_image) || null;
          const stepImages = parsed.step_images || (parsed.structured && parsed.structured.step_images) || undefined;
          // If there's text, yield it as a final content chunk
          if (finalText) yield { content: finalText };
          // Yield final metadata
          yield { threadId: thread_id, stepImage: stepImage, stepImages };
        } else if (parsed.type === 'error') {
          const content = parsed.content || parsed.error || JSON.stringify(parsed);
          throw new Error(content);
        } else {
          // Fallback: try to extract text-like fields
          const maybeText = parsed.content || parsed.message || (parsed.structured && parsed.structured.text);
          if (maybeText) yield { content: String(maybeText) };
        }
      }
    }

    // If any leftover buffer after stream end, attempt to parse it
    const leftover = buffer.trim();
    if (leftover) {
      const lines = leftover.split(/\r?\n/).filter(Boolean);
      const dataLines = lines.filter((l) => l.startsWith('data:'));
      if (dataLines.length) {
        const payload = dataLines.map((l) => l.replace(/^data:\s?/, '')).join('\n');
        try {
          const parsed = JSON.parse(payload);
          const finalText = (parsed.message || (parsed.structured && parsed.structured.text)) || '';
          const thread_id = parsed.thread_id || parsed.threadId || parsed.thread;
          const stepImage = parsed.step_image || (parsed.structured && parsed.structured.step_image) || null;
          const stepImages = parsed.step_images || (parsed.structured && parsed.structured.step_images) || undefined;
          if (finalText) yield { content: finalText };
          yield { threadId: thread_id, stepImage: stepImage, stepImages };
        } catch (err) {
          // ignore
        }
      }
    }
  }

  // Fetch session list
  async getSessions(): Promise<{ sessions: any[] }> {
    const res = await fetch(`${API_BASE_URL}/chat/sessions`, { headers: this.getAuthHeaders() });
    if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
    return await res.json();
  }

  // Fetch chat history for a thread. Returns an array of Message objects.
  async getChatHistory(threadId: string): Promise<Message[]> {
    const url = new URL(`${API_BASE_URL}/chat/history`);
    url.searchParams.set('thread_id', threadId);
    const res = await fetch(url.toString(), { headers: this.getAuthHeaders() });
    if (!res.ok) throw new Error(`Failed to load history: ${res.status}`);
    const data = await res.json();
    return (data.messages || []).map((m: any) => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
      step_image: m.step_image,
      step_images: m.step_images
    }));
  }

  // Clear chat history (all or a specific thread)
  async clearChatHistory(threadId?: string) {
    const url = new URL(`${API_BASE_URL}/chat/history`);
    if (threadId) url.searchParams.set('thread_id', threadId);
    const res = await fetch(url.toString(), { method: 'DELETE', headers: this.getAuthHeaders() });
    if (!res.ok) throw new Error(`Failed to clear history: ${res.status}`);
    return await res.json();
  }
}

export const apiService = new ApiService();


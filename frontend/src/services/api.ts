const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
  };
  message: string;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export class ApiService {
  private token: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  setToken(token: string, refreshToken?: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
    if (refreshToken) {
      this.refreshToken = refreshToken;
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  clearToken() {
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
  }

  getAuthHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  private async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;
    
    try {
      const response = await fetch(`${API_BASE_URL}/refresh`, {
        method: 'POST',
        headers: {
          'Refresh-Token': this.refreshToken,
        },
      });

      if (response.ok) {
        const data = await response.json();
        this.setToken(data.access_token, data.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
    
    return false;
  }

  private async ensureOk(response: Response, retryOnAuth = true) {
    if (response.ok) return response;
    
    // Try to refresh token on 401
    if (response.status === 401 && retryOnAuth && this.refreshToken) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        // Token refreshed, caller should retry the request
        throw new Error('TOKEN_REFRESHED');
      }
    }
    
    const body = await response.text().catch(() => '');
    const err = new Error(`HTTP ${response.status}: ${body || response.statusText}`);
    
    // Clear tokens only if refresh also failed
    if (response.status === 401) {
      this.clearToken();
    }
    throw err;
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token, data.refresh_token);
    return data;
  }

  async signup(credentials: LoginRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      throw new Error('Signup failed');
    }
  }

  async *streamMessage(message: string, threadId?: string): AsyncGenerator<{ content: string; threadId?: string }, void, unknown> {
    const headers: HeadersInit = {
      ...this.getAuthHeaders(),
      'Accept': 'text/event-stream',
    };

    const body: ChatRequest = { message };
    if (threadId) {
      body.thread_id = threadId;
    }

    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error('Failed to stream message');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let boundaryIndex;
        // Process complete SSE events separated by double newlines
        while ((boundaryIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);

          // Extract data lines (can be multiple)
          const dataLines = rawEvent
            .split('\n')
            .filter((l) => l.startsWith('data: '))
            .map((l) => l.slice(6))
            .join('\n');

          const trimmed = dataLines.trim();
          if (!trimmed) continue;

          try {
            const parsed = JSON.parse(trimmed);
            if (parsed.type === 'token') {
              yield { content: parsed.content };
            } else if (parsed.type === 'status') {
              // Show status with proper spacing
              yield { content: `\n\n*${parsed.content}*\n\n` };
            } else if (parsed.type === 'done' && parsed.thread_id) {
              yield { content: '', threadId: parsed.thread_id };
            } else if (parsed.type === 'error') {
              throw new Error(parsed.content);
            }
          } catch (e) {
            // Silently ignore parse errors in production
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async getChatHistory(threadId?: string): Promise<Message[]> {
    const url = threadId 
      ? `${API_BASE_URL}/chat/history?thread_id=${encodeURIComponent(threadId)}`
      : `${API_BASE_URL}/chat/history`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });
    await this.ensureOk(response);

    const data = await response.json();
    return data.messages || [];
  }

  async clearChatHistory(threadId?: string): Promise<void> {
    const url = threadId 
      ? `${API_BASE_URL}/chat/history?thread_id=${encodeURIComponent(threadId)}`
      : `${API_BASE_URL}/chat/history`;
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    await this.ensureOk(response);
  }

  async getSessions(): Promise<{ sessions: Array<{ id: string; title: string; preview: string; timestamp: string; message_count: number }> }> {
    const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });
    await this.ensureOk(response);
    return await response.json();
  }
}

export const apiService = new ApiService();

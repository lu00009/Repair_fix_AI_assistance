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
}

export interface ChatResponse {
  response: string;
  thread_id: string;
}

export class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
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

  private async ensureOk(response: Response) {
    if (response.ok) return response;
    const body = await response.text().catch(() => '');
    const err = new Error(`HTTP ${response.status}: ${body || response.statusText}`);
    // Auto-logout on 401
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
    this.setToken(data.access_token);
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

  async sendMessage(message: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ message }),
    });
    await this.ensureOk(response);
    return response.json();
  }

  async *streamMessage(message: string): AsyncGenerator<string, void, unknown> {
    const headers: HeadersInit = {
      ...this.getAuthHeaders(),
      'Accept': 'text/event-stream',
    };

    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message }),
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
              yield parsed.content;
            } else if (parsed.type === 'status') {
              yield `\n\n_${parsed.content}_\n\n`;
            } else if (parsed.type === 'error') {
              throw new Error(parsed.content);
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', trimmed);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async getChatHistory(): Promise<Message[]> {
    const response = await fetch(`${API_BASE_URL}/chat/history`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });
    await this.ensureOk(response);

    const data = await response.json();
    return data.messages || [];
  }

  async clearChatHistory(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chat/history`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    await this.ensureOk(response);
  }
}

export const apiService = new ApiService();

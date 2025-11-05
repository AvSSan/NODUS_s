# TypeScript/React примеры интеграции с NODUS_s API

## 🔧 Установка зависимостей

```bash
npm install axios
# или
yarn add axios
```

---

## 📦 TypeScript типы

### `types/api.ts`

```typescript
// Модели данных
export interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface Chat {
  id: number;
  title: string;
  is_group: boolean;
  created_at: string;
}

export interface Message {
  id: number;
  chat_id: number;
  author_id: number | null;
  type: 'text' | 'voice' | 'system';
  content: string | null;
  payload: Record<string, any> | null;
  ts: string;
}

export interface VoicePayload {
  attachment_id: string;
  duration_ms: number;
  codec: string;
  waveform?: number[];
}

// Auth
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
  avatar_url?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// Chats
export interface CreateChatRequest {
  title: string;
  is_group: boolean;
  member_ids: number[];
}

export interface UpdateChatRequest {
  title?: string;
}

// Messages
export interface CreateMessageRequest {
  chat_id: number;
  type: string;
  content?: string;
  payload?: Record<string, any>;
}

export interface UpdateMessageRequest {
  content?: string;
  payload?: Record<string, any>;
}

// Attachments
export interface PresignedRequest {
  filename: string;
  content_type: string;
}

export interface PresignedResponse {
  attachment_id: string;
  url: string;
  fields: Record<string, string>;
  expires_at: string;
}

// WebSocket
export interface WSEvent {
  event: 'message.created' | 'message.updated';
  data: Message;
}
```

---

## 🔐 Auth Service

### `services/auth.service.ts`

```typescript
import axios, { AxiosInstance } from 'axios';
import {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  TokenPair,
  User,
} from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

class AuthService {
  private api: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Загрузить токены из localStorage
    this.loadTokens();

    // Interceptor для добавления токена
    this.api.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    // Interceptor для обработки 401 и рефреша
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refresh();
            originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            return this.api(originalRequest);
          } catch (refreshError) {
            this.logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private loadTokens() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  private saveTokens(tokens: TokenPair) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await this.api.post<AuthResponse>('/auth/register', data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    this.saveTokens(response.data.tokens);
    return response.data;
  }

  async login(data: LoginRequest): Promise<TokenPair> {
    const response = await this.api.post<TokenPair>('/auth/login', data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    this.saveTokens(response.data);
    return response.data;
  }

  async refresh(): Promise<TokenPair> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post<TokenPair>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: this.refreshToken }
    );

    this.saveTokens(response.data);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get<User>('/users/me');
    return response.data;
  }

  logout() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  getApi(): AxiosInstance {
    return this.api;
  }
}

export default new AuthService();
```

---

## 💬 Chat Service

### `services/chat.service.ts`

```typescript
import authService from './auth.service';
import { Chat, CreateChatRequest, UpdateChatRequest } from '../types/api';

class ChatService {
  async getChats(): Promise<Chat[]> {
    const api = authService.getApi();
    const response = await api.get<Chat[]>('/chats');
    return response.data;
  }

  async getChat(chatId: number): Promise<Chat> {
    const api = authService.getApi();
    const response = await api.get<Chat>(`/chats/${chatId}`);
    return response.data;
  }

  async createChat(data: CreateChatRequest): Promise<Chat> {
    const api = authService.getApi();
    const response = await api.post<Chat>('/chats', data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    return response.data;
  }

  async updateChat(chatId: number, data: UpdateChatRequest): Promise<Chat> {
    const api = authService.getApi();
    const response = await api.patch<Chat>(`/chats/${chatId}`, data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    return response.data;
  }

  async deleteChat(chatId: number): Promise<void> {
    const api = authService.getApi();
    await api.delete(`/chats/${chatId}`, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
  }
}

export default new ChatService();
```

---

## 📨 Message Service

### `services/message.service.ts`

```typescript
import authService from './auth.service';
import {
  Message,
  CreateMessageRequest,
  UpdateMessageRequest,
} from '../types/api';

class MessageService {
  async getMessages(chatId: number): Promise<Message[]> {
    const api = authService.getApi();
    const response = await api.get<Message[]>('/messages', {
      params: { chat_id: chatId },
    });
    return response.data;
  }

  async createMessage(data: CreateMessageRequest): Promise<Message> {
    const api = authService.getApi();
    const response = await api.post<Message>('/messages', data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    return response.data;
  }

  async updateMessage(
    messageId: number,
    data: UpdateMessageRequest
  ): Promise<Message> {
    const api = authService.getApi();
    const response = await api.patch<Message>(
      `/messages/${messageId}`,
      data,
      {
        headers: {
          'Idempotency-Key': crypto.randomUUID(),
        },
      }
    );
    return response.data;
  }
}

export default new MessageService();
```

---

## 📎 Attachment Service

### `services/attachment.service.ts`

```typescript
import authService from './auth.service';
import { PresignedRequest, PresignedResponse } from '../types/api';

class AttachmentService {
  async getPresignedUrl(data: PresignedRequest): Promise<PresignedResponse> {
    const api = authService.getApi();
    const response = await api.post<PresignedResponse>('/attachments', data, {
      headers: {
        'Idempotency-Key': crypto.randomUUID(),
      },
    });
    return response.data;
  }

  async uploadFile(
    presigned: PresignedResponse,
    file: Blob
  ): Promise<void> {
    const formData = new FormData();
    
    // Добавить поля из presigned
    Object.entries(presigned.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    
    // Добавить файл
    formData.append('file', file);

    // Загрузить на S3
    await fetch(presigned.url, {
      method: 'POST',
      body: formData,
    });
  }

  async uploadAudio(audioBlob: Blob, filename: string = 'voice.opus'): Promise<string> {
    // 1. Получить presigned URL
    const presigned = await this.getPresignedUrl({
      filename,
      content_type: 'audio/opus',
    });

    // 2. Загрузить файл
    await this.uploadFile(presigned, audioBlob);

    // 3. Вернуть attachment_id
    return presigned.attachment_id;
  }
}

export default new AttachmentService();
```

---

## 🔌 WebSocket Service

### `services/websocket.service.ts`

```typescript
import { WSEvent } from '../types/api';

type EventHandler = (event: WSEvent) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: EventHandler[] = [];
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        this.handlers.forEach((handler) => handler(data));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
      this.connect();
    }, this.reconnectDelay);
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(handler: EventHandler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }
}

export default new WebSocketService();
```

---

## ⚛️ React Hooks

### `hooks/useAuth.ts`

```typescript
import { useState, useEffect } from 'react';
import authService from '../services/auth.service';
import { User } from '../types/api';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      if (authService.isAuthenticated()) {
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error('Failed to load user:', error);
          authService.logout();
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (email: string, password: string) => {
    await authService.login({ email, password });
    const currentUser = await authService.getCurrentUser();
    setUser(currentUser);
  };

  const register = async (email: string, password: string, displayName: string) => {
    const response = await authService.register({
      email,
      password,
      display_name: displayName,
    });
    setUser(response.user);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return { user, loading, login, register, logout };
}
```

### `hooks/useChats.ts`

```typescript
import { useState, useEffect } from 'react';
import chatService from '../services/chat.service';
import { Chat } from '../types/api';

export function useChats() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadChats = async () => {
    try {
      setLoading(true);
      const data = await chatService.getChats();
      setChats(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChats();
  }, []);

  const createChat = async (title: string, memberIds: number[], isGroup = true) => {
    const newChat = await chatService.createChat({
      title,
      is_group: isGroup,
      member_ids: memberIds,
    });
    setChats((prev) => [newChat, ...prev]);
    return newChat;
  };

  const updateChat = async (chatId: number, title: string) => {
    const updatedChat = await chatService.updateChat(chatId, { title });
    setChats((prev) =>
      prev.map((chat) => (chat.id === chatId ? updatedChat : chat))
    );
    return updatedChat;
  };

  const deleteChat = async (chatId: number) => {
    await chatService.deleteChat(chatId);
    setChats((prev) => prev.filter((chat) => chat.id !== chatId));
  };

  return { chats, loading, error, createChat, updateChat, deleteChat, reload: loadChats };
}
```

### `hooks/useMessages.ts`

```typescript
import { useState, useEffect } from 'react';
import messageService from '../services/message.service';
import { Message } from '../types/api';

export function useMessages(chatId: number | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadMessages = async () => {
    if (!chatId) return;

    try {
      setLoading(true);
      const data = await messageService.getMessages(chatId);
      setMessages(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, [chatId]);

  const sendMessage = async (type: string, content?: string, payload?: any) => {
    if (!chatId) return;

    const newMessage = await messageService.createMessage({
      chat_id: chatId,
      type,
      content,
      payload,
    });

    setMessages((prev) => [newMessage, ...prev]);
    return newMessage;
  };

  const updateMessage = async (messageId: number, content?: string, payload?: any) => {
    const updatedMessage = await messageService.updateMessage(messageId, {
      content,
      payload,
    });

    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? updatedMessage : msg))
    );
    return updatedMessage;
  };

  const addMessage = (message: Message) => {
    setMessages((prev) => {
      // Проверить, нет ли уже этого сообщения
      if (prev.some((m) => m.id === message.id)) {
        return prev;
      }
      return [message, ...prev];
    });
  };

  return {
    messages,
    loading,
    error,
    sendMessage,
    updateMessage,
    addMessage,
    reload: loadMessages,
  };
}
```

### `hooks/useWebSocket.ts`

```typescript
import { useEffect } from 'react';
import websocketService from '../services/websocket.service';
import { WSEvent } from '../types/api';

export function useWebSocket(onEvent: (event: WSEvent) => void) {
  useEffect(() => {
    websocketService.connect();
    const unsubscribe = websocketService.subscribe(onEvent);

    return () => {
      unsubscribe();
      websocketService.disconnect();
    };
  }, [onEvent]);
}
```

---

## 📱 Примеры компонентов

### `components/ChatList.tsx`

```typescript
import React from 'react';
import { useChats } from '../hooks/useChats';

export const ChatList: React.FC = () => {
  const { chats, loading, error } = useChats();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="chat-list">
      {chats.map((chat) => (
        <div key={chat.id} className="chat-item">
          <h3>{chat.title}</h3>
          <p>{chat.is_group ? 'Group' : 'Direct'}</p>
        </div>
      ))}
    </div>
  );
};
```

### `components/ChatWindow.tsx`

```typescript
import React, { useState, useCallback } from 'react';
import { useMessages } from '../hooks/useMessages';
import { useWebSocket } from '../hooks/useWebSocket';
import { WSEvent } from '../types/api';

interface ChatWindowProps {
  chatId: number;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ chatId }) => {
  const { messages, sendMessage, addMessage } = useMessages(chatId);
  const [inputText, setInputText] = useState('');

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      if (event.data.chat_id === chatId) {
        if (event.event === 'message.created') {
          addMessage(event.data);
        }
      }
    },
    [chatId, addMessage]
  );

  useWebSocket(handleWSEvent);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    await sendMessage('text', inputText);
    setInputText('');
  };

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((message) => (
          <div key={message.id} className="message">
            <strong>User {message.author_id}:</strong> {message.content}
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};
```

---

## 🎤 Пример отправки голосового сообщения

```typescript
import attachmentService from '../services/attachment.service';
import messageService from '../services/message.service';

async function sendVoiceMessage(
  chatId: number,
  audioBlob: Blob,
  durationMs: number
): Promise<void> {
  try {
    // 1. Загрузить аудио и получить attachment_id
    const attachmentId = await attachmentService.uploadAudio(audioBlob);

    // 2. Создать сообщение с голосовым вложением
    await messageService.createMessage({
      chat_id: chatId,
      type: 'voice',
      payload: {
        attachment_id: attachmentId,
        duration_ms: durationMs,
        codec: 'opus',
      },
    });

    console.log('Voice message sent successfully');
  } catch (error) {
    console.error('Failed to send voice message:', error);
    throw error;
  }
}
```

---

## 🧪 Testing Example

### `__tests__/auth.service.test.ts`

```typescript
import authService from '../services/auth.service';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.json({
        access_token: 'test_access_token',
        refresh_token: 'test_refresh_token',
        token_type: 'bearer',
        expires_in: 900,
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('AuthService', () => {
  it('should login successfully', async () => {
    const tokens = await authService.login({
      email: 'test@example.com',
      password: 'password123',
    });

    expect(tokens.access_token).toBe('test_access_token');
    expect(authService.isAuthenticated()).toBe(true);
  });
});
```

---

**Документация актуальна для версии API 1.0.0**

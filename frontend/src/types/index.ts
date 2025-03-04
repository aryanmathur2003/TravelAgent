export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface WebSocketMessage {
  type: string;
  message: string;
  role?: string;
} 
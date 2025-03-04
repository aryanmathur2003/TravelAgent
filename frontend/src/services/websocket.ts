import { ChatMessage, WebSocketMessage } from '../types';

class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: ((message: WebSocketMessage) => void)[] = [];

  connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log('WebSocket connection established');
        resolve();
      };

      this.socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as WebSocketMessage;
        this.messageHandlers.forEach(handler => handler(data));
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.socket.onclose = () => {
        console.log('WebSocket connection closed');
      };
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  sendMessage(messages: ChatMessage[], model: string = 'gpt-3.5-turbo', temperature: number = 0.7): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const payload = {
        messages,
        model,
        temperature
      };
      this.socket.send(JSON.stringify(payload));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  onMessage(handler: (message: WebSocketMessage) => void): void {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler: (message: WebSocketMessage) => void): void {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }
}

export default new WebSocketService(); 
import React, { useEffect, useState, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { ChatMessage as ChatMessageType, WebSocketMessage } from '../types';
import websocketService from '../services/websocket';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([
    {
      role: 'system',
      content: 'You are a helpful assistant.'
    }
  ]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const processedMessagesRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const connectWebSocket = async () => {
      try {
        await websocketService.connect('ws://localhost:8000/ws/chat');
        setIsConnected(true);
      } catch (error) {
        console.error('Failed to connect to WebSocket:', error);
        setTimeout(connectWebSocket, 3000); // Try to reconnect after 3 seconds
      }
    };

    connectWebSocket();

    websocketService.onMessage(handleWebSocketMessage);

    return () => {
      websocketService.disconnect();
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleWebSocketMessage = (data: WebSocketMessage) => {
    if (data.type === 'chat_response' && data.role && data.message) {
      const messageId = `${data.role}:${data.message}`;
      
      if (!processedMessagesRef.current.has(messageId)) {
        processedMessagesRef.current.add(messageId);
        
        setMessages(prev => [
          ...prev,
          { role: data.role as 'assistant', content: data.message }
        ]);
      }
      
      setIsLoading(false);
    } else if (data.type === 'message_received') {
      console.log('Server received message:', data.message);
    }
  };

  const handleSendMessage = (content: string) => {
    const userMessage: ChatMessageType = { role: 'user', content };
    
    setMessages(prev => [...prev, userMessage]);
    
    setIsLoading(true);
    
    websocketService.sendMessage([...messages, userMessage]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-grow overflow-y-auto p-4">
        {!isConnected && (
          <div className="text-center p-4 bg-yellow-100 text-yellow-800 rounded">
            Connecting to server...
          </div>
        )}
        
        {messages.slice(1).map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-200 text-gray-800 p-4 rounded-lg rounded-bl-none">
              <p>Thinking...</p>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default Chat; 
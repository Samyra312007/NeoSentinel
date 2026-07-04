import { useState, useEffect, useRef, useCallback } from 'react';
import type { WebSocketEvent } from '../types/telemetry';

export interface UseWebSocketReturn<T = WebSocketEvent> {
  connected: boolean;
  error: string | null;
  lastMessage: T | null;
  messages: T[];
  sendMessage: (message: string) => void;
}

export function useWebSocket<T = WebSocketEvent>(url: string = 'ws://localhost:8080/ws'): UseWebSocketReturn<T> {
  const [connected, setConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [messages, setMessages] = useState<T[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setLastMessage(parsed);
          setMessages((prev) => [...prev, parsed]);
        } catch (e) {
          setLastMessage(event.data as unknown as T);
          setMessages((prev) => [...prev, event.data as unknown as T]);
        }
      };

      ws.onerror = () => {
        setError('WebSocket error occurred');
      };

      ws.onclose = () => {
        setConnected(false);
      };
    } catch (err: any) {
      setError(err.message || 'Failed to connect');
    }

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  return { connected, error, lastMessage, messages, sendMessage };
}

import { useEffect, useRef, useState, useCallback } from 'react';

export function useSSE<T>(url: string, onMessage: (data: T) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelay = useRef(1000);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      reconnectDelay.current = 1000;
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("Failed to parse SSE data", e);
      }
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      
      // Exponential backoff
      const delay = reconnectDelay.current;
      reconnectDelay.current = Math.min(delay * 2, 30000);
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log(`Reconnecting to SSE in ${delay}ms...`);
        connectRef.current();
      }, delay);
    };
  }, [url, onMessage]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { isConnected };
}

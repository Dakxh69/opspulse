/**
 * OpsPulse Frontend — Realtime WebSocket Hook
 *
 * Implements persistent connection with jittered exponential backoff reconnect
 * and fallback refresh notification per spec Section 15.
 */

import { useEffect, useRef, useState } from 'react';

export interface WebSocketEvent {
  event: string;
  data: Record<string, unknown>;
}

export function useWebSocket(onEvent?: (event: WebSocketEvent) => void) {
  const [status, setStatus] = useState<'CONNECTING' | 'CONNECTED' | 'DISCONNECTED'>('DISCONNECTED');
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      setStatus('CONNECTING');

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/ws`;

      try {
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (unmounted) return;
          setStatus('CONNECTED');
          retryCountRef.current = 0;
        };

        socket.onmessage = (event) => {
          try {
            const parsed: WebSocketEvent = JSON.parse(event.data);
            if (onEvent) onEvent(parsed);
          } catch {
            // Non-JSON message (e.g. pong)
          }
        };

        socket.onclose = () => {
          if (unmounted) return;
          setStatus('DISCONNECTED');
          scheduleReconnect();
        };

        socket.onerror = () => {
          socket.close();
        };
      } catch {
        scheduleReconnect();
      }
    };

    const scheduleReconnect = () => {
      const delay = Math.min(1000 * Math.pow(2, retryCountRef.current) + Math.random() * 500, 15000);
      retryCountRef.current += 1;
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return { status };
}

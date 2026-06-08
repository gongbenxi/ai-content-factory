import { useState, useEffect, useRef } from 'react';

interface SSEEvent {
  id?: number;
  event: string;
  data: any;
}

export function useSSE(runId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    setEvents([]);
    if (!runId) return;

    const es = new EventSource(`/api/runs/${runId}/stream`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    const handleEvent = (eventName: string) => (e: MessageEvent) => {
      const id = e.lastEventId ? Number(e.lastEventId) : undefined;
      try {
        const parsed = JSON.parse(e.data);
        setEvents((prev) => [...prev, { id, event: eventName, data: parsed }].slice(-1000));
      } catch {
        setEvents((prev) => [...prev, { id, event: eventName, data: e.data }].slice(-1000));
      }
    };

    es.onmessage = handleEvent("message");
    [
      "graph.start",
      "graph.done",
      "graph.error",
      "agent.start",
      "agent.done",
      "agent.warning",
      "agent.token",
      "tool.call",
      "writer.token",
      "image.generated",
      "review.done",
      "budget.warning",
      "needs_human",
      "heartbeat",
    ].forEach((eventName) => es.addEventListener(eventName, handleEvent(eventName)));

    return () => {
      es.close();
      esRef.current = null;
      setConnected(false);
    };
  }, [runId]);

  return { events, connected };
}

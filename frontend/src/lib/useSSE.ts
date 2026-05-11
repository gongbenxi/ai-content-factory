import { useState, useEffect, useRef } from 'react';

interface SSEEvent {
  event: string;
  data: any;
}

export function useSSE(runId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;

    const es = new EventSource(`/api/runs/${runId}/stream`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    const handleEvent = (eventName: string) => (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        setEvents((prev) => [...prev, { event: eventName, data: parsed }]);
      } catch {
        setEvents((prev) => [...prev, { event: eventName, data: e.data }]);
      }
    };

    es.onmessage = handleEvent("message");
    [
      "graph.start",
      "graph.done",
      "graph.error",
      "agent.start",
      "agent.done",
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

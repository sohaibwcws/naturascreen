"use client";

import { useEffect, useRef, useState } from "react";
import type { SimEnd, SimFrame, SimMeta, StreamStatus } from "./types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";

export interface StreamResult {
  meta: SimMeta | null;
  frames: SimFrame[];
  end: SimEnd | null;
  status: StreamStatus;
  error: string | null;
}

/**
 * Connect to a simulation websocket and buffer its frames.
 *
 * `path` is the API path (e.g. "/simulate/stream?effectiveness=0.6"). Pass null to stay
 * idle. The full buffer is retained so the player can scrub/replay after streaming ends.
 */
export function useSimulationStream(path: string | null): StreamResult {
  const [meta, setMeta] = useState<SimMeta | null>(null);
  const [frames, setFrames] = useState<SimFrame[]>([]);
  const [end, setEnd] = useState<SimEnd | null>(null);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!path) {
      setStatus("idle");
      return;
    }
    setMeta(null);
    setFrames([]);
    setEnd(null);
    setError(null);
    setStatus("connecting");

    const ws = new WebSocket(`${WS_BASE}${path}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as SimMeta | SimFrame | SimEnd;
      if (msg.type === "meta") {
        setMeta(msg);
        setStatus("streaming");
      } else if (msg.type === "frame") {
        setFrames((prev) => [...prev, msg]);
      } else if (msg.type === "end") {
        setEnd(msg);
        setStatus("done");
      }
    };
    ws.onerror = () => {
      setError("stream connection failed");
      setStatus("error");
    };
    ws.onclose = () => {
      setStatus((s) => (s === "streaming" || s === "connecting" ? "done" : s));
    };

    return () => {
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
    };
  }, [path]);

  return { meta, frames, end, status, error };
}

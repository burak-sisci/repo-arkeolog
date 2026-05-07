const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function createProgressSocket(
  analysisId: string,
  onMessage: (data: { stage: string; message: string; progress_pct: number }) => void,
  onClose?: () => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/progress/${analysisId}`);
  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {}
  };
  if (onClose) ws.onclose = onClose;
  return ws;
}

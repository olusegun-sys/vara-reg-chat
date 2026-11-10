const BASE_URL = import.meta.env.VITE_API_URL || "";

export async function getJurisdictions() {
  const response = await fetch(`${BASE_URL}/api/jurisdictions`);
  if (!response.ok) throw new Error("Could not load jurisdictions.");
  return response.json();
}

export async function generateChatTitle(question) {
  try {
    const response = await fetch(`${BASE_URL}/api/title`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.title;
  } catch {
    return null;
  }
}

export async function streamChat(question, jurisdiction, history, onChunk, onSources) {
  // Note: the previous "Warming up the AI… (cold start)" indicator was
  // removed on 2026-11-10. The backend sends heartbeat SSE comments
  // (`: keep-alive\n\n`) every 2 seconds during long LLM calls, so the
  // HTTP connection stays alive. The 4s timeout that used to fire this
  // message was misleading — it fired on any >4s wait, including normal
  // LLM generation time, not just Render cold starts.

  let response;
  try {
    response = await fetch(`${BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        jurisdiction,
        history: history || []
      }),
    });
  } catch (err) {
    throw err;
  }

  if (!response.ok) {
    let detail = "The AI service is temporarily unavailable. Please try again in a moment.";
    try {
      const err = await response.json();
      // If it's a 500 with "embedding" or "Cohere" in the message, use the friendly text
      if (response.status === 500 && (err.detail || "").toLowerCase().includes("embedding")) {
        detail = "The AI service is temporarily unavailable (Cohere connection). Please try again in 60 seconds.";
      } else if (err.detail) {
        detail = err.detail;
      }
    } catch {}
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  // SSE BUFFERING
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      for (const line of event.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const dataStr = line.slice(6).trim();
        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);
          if (data.type === "sources") {
            onSources(data.sources);
          } else if (data.type === "text") {
            onChunk(data.text);
          }
        } catch (e) {
          console.warn("Skipping malformed SSE event:", dataStr.slice(0, 80));
        }
      }
    }
  }

  // Flush any trailing event if the stream ended without "\n\n".
  if (buffer.trim()) {
    for (const line of buffer.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6).trim());
        if (data.type === "sources") onSources(data.sources);
        else if (data.type === "text") onChunk(data.text);
      } catch {
        // ignore — likely a partial heartbeat
      }
    }
  }
}

export async function extractFacts(sessionId, userMessage) {
  try {
    const response = await fetch(`${BASE_URL}/api/memory/facts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, user_message: userMessage }),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.facts || [];
  } catch {
    return [];
  }
}
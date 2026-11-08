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

export async function streamChat(question, jurisdiction, history, onChunk, onSources, onWarming) {
  // If the server doesn't send the first byte within 4 seconds, the user
  // will see a "Warming up" message. This happens on Render's free tier
  // when the backend has been idle for 15+ min and the container is cold.
  let firstByteReceived = false;
  const warmingTimeout = setTimeout(() => {
    if (!firstByteReceived && onWarming) {
      console.log("[client] Backend cold start detected — showing warmup message");
      onWarming(true);
    }
  }, 4000);

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
    clearTimeout(warmingTimeout);
    if (onWarming) onWarming(false);
    throw err;
  }

  if (!response.ok) {
    clearTimeout(warmingTimeout);
    if (onWarming) onWarming(false);
    let detail = "Something went wrong.";
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // First byte arrived — clear the warming message
    if (!firstByteReceived) {
      firstByteReceived = true;
      clearTimeout(warmingTimeout);
      if (onWarming) onWarming(false);
    }

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

  if (buffer.trim()) {
    for (const line of buffer.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6).trim());
        if (data.type === "sources") onSources(data.sources);
        else if (data.type === "text") onChunk(data.text);
      } catch {}
    }
  }

  clearTimeout(warmingTimeout);
  if (onWarming) onWarming(false);
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
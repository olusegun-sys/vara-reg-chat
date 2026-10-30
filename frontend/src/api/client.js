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
  const response = await fetch(`${BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      question, 
      jurisdiction,
      history: history || []
    }),
  });

  if (!response.ok) {
    let detail = "Something went wrong.";
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  
  // SSE BUFFERING FIX
  // Network reads don't respect event boundaries. A single read can
  // contain half an event (`data: {"type":"te`) or multiple events merged.
  // The old code did `chunk.split("\n")` on each read, which threw a
  // "Unterminated string in JSON" on partial chunks. This bug silently
  // dropped some text chunks (caught by try/catch), causing the console
  // errors you saw on long responses like Q3.
  //
  // The correct pattern: maintain a buffer across reads, split on the
  // true SSE event terminator "\n\n", and keep the incomplete tail in
  // the buffer for the next read. Complete events are never split.
  let buffer = "";
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    
    // SSE events are separated by a blank line ("\n\n").
    const events = buffer.split("\n\n");
    // The last element is the incomplete tail; keep it for next read.
    buffer = events.pop() || "";
    
    for (const event of events) {
      // Within a single event, there can be multiple "data: " lines
      // (rare in our backend, but standard SSE allows it).
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
          // warn (not error): a malformed heartbeat or keepalive is benign.
          // A real bug here would be caught by the fact that text is missing.
          console.warn("Skipping malformed SSE event:", dataStr.slice(0, 80));
        }
      }
    }
  }
  
  // Edge case: if the stream ends without a trailing "\n\n", the last
  // event may still be in the buffer. Try to flush it.
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
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getJurisdictions() {
  const response = await fetch(`${BASE_URL}/api/jurisdictions`);
  if (!response.ok) throw new Error("Could not load jurisdictions.");
  return response.json();
}

// Generate title (keep as is)
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

// STREAMING CHAT FUNCTION
// Why streaming: Waits 0 seconds. Renders the text as it arrives from the LLM.
export async function streamChat(question, jurisdiction, onChunk, onSources) {
  const response = await fetch(`${BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, jurisdiction }),
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
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");
    
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const dataStr = line.replace("data: ", "").trim();
        if (!dataStr) continue;
        
        try {
          const data = JSON.parse(dataStr);
          if (data.type === "sources") {
            onSources(data.sources);
          } else if (data.type === "text") {
            onChunk(data.text);
          }
        } catch (e) {
          console.error("Parse error:", e);
        }
      }
    }
  }
}
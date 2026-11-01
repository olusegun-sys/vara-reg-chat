import { useEffect, useState, useCallback, useRef } from "react";
import JurisdictionSelector from "./components/JurisdictionSelector.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Sidebar from "./components/Sidebar.jsx";
import { getJurisdictions, streamChat, generateChatTitle, extractFacts } from "./api/client.js";
import { 
  getSessions, createSession, getMessages, addMessage, 
  updateSessionTitle, deleteSession, togglePin,
  getSessionFacts, saveSessionFacts
} from "./api/supabase.js";

const SESSION_OPENING = 2;
const RECENT_WINDOW = 8;
const SESSION_STORAGE_KEY = "vara_current_session_id";

export default function App() {
  const [jurisdictions, setJurisdictions] = useState([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    try {
      return localStorage.getItem(SESSION_STORAGE_KEY) || null;
    } catch {
      return null;
    }
  });
  const [messages, setMessages] = useState([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Refs used to protect the message-loading effect from clobbering in-flight sends.
  const justSentRef = useRef(false);
  const skipNextFetchRef = useRef(false);   // NEW: skip the fetch triggered by createSession
  const sendingInProgressRef = useRef(false); // NEW: true for the entire duration of handleSend

  useEffect(() => {
    getJurisdictions().then(data => {
      setJurisdictions(data);
      if (data.length > 0) setSelectedJurisdiction(data[0].code);
    }).catch(err => setLoadError(err.message));
  }, []);

  useEffect(() => {
    getSessions().then(data => {
      setSessions(data);
      const stored = localStorage.getItem(SESSION_STORAGE_KEY);
      if (stored && !data.some(s => s.id === stored)) {
        console.warn("[app] Stored session ID not found, clearing.");
        localStorage.removeItem(SESSION_STORAGE_KEY);
        setCurrentSessionId(null);
      }
    }).catch(err => console.error("Error loading sessions:", err));
  }, []);

  useEffect(() => {
    try {
      if (currentSessionId) {
        localStorage.setItem(SESSION_STORAGE_KEY, currentSessionId);
      } else {
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    } catch (e) {
      console.warn("[app] Could not persist session ID:", e);
    }
  }, [currentSessionId]);

  useEffect(() => {
    if (!currentSessionId) {
      setMessages([]); 
      setIsLoadingMessages(false);
      return;
    }

    // Guard 1: if a send is currently in progress (from handleSend), do not
    // fetch. The send flow manages its own message state.
    if (sendingInProgressRef.current) {
      return;
    }

    // Guard 2: if handleSend just created this session and is about to add the
    // first user message + assistant placeholder, do not fetch — otherwise
    // getMessages can resolve AFTER the placeholder is set and overwrite it,
    // causing the streaming text to land in the user message's content field
    // (which renders as a blue bubble with raw markdown).
    if (skipNextFetchRef.current) {
      skipNextFetchRef.current = false;
      return;
    }

    // Guard 3: the classic post-send guard.
    if (isSending) return;
    if (justSentRef.current) {
      justSentRef.current = false;
      return;
    }

    setIsLoadingMessages(true);
    getMessages(currentSessionId)
      .then(data => {
        setMessages(data.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources
        })));
      })
      .catch(err => console.error("Error loading messages:", err))
      .finally(() => setIsLoadingMessages(false));
  }, [currentSessionId, isSending]);

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setInputValue("");
  };

  const handleSelectSession = (id) => {
    setCurrentSessionId(id);
    setInputValue("");
  };

  const handleRename = async (id, newTitle) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, title: newTitle } : s));
    await updateSessionTitle(id, newTitle);
  };

  const handleDelete = async (id) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(null); 
    }
    await deleteSession(id);
  };

  const handleTogglePin = async (id) => {
    const session = sessions.find(s => s.id === id);
    if (!session) return;
    const newPinnedState = !session.is_pinned;
    setSessions(prev => {
      const updated = prev.map(s => s.id === id ? { ...s, is_pinned: newPinnedState } : s);
      return updated.sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return new Date(b.created_at) - new Date(a.created_at);
      });
    });
    await togglePin(id, newPinnedState);
  };

  const handleEditMessage = (content) => {
    setInputValue(content);
  };

  const handleSend = useCallback(async () => {
    const question = inputValue.trim();
    if (!question || isSending || !selectedJurisdiction) return;

    // Set the in-progress flag BEFORE any await. The message-loading effect
    // checks this and bails — preventing the getMessages overwrite that
    // produces the "AI answer in user bubble with asterisks" bug.
    sendingInProgressRef.current = true;

    let activeSessionId = currentSessionId;
    
    if (!activeSessionId) {
      try {
        const newSession = await createSession("New Conversation");
        setSessions(prev => [newSession, ...prev]);
        // Skip the fetch that would otherwise trigger on this change.
        skipNextFetchRef.current = true;
        setCurrentSessionId(newSession.id);
        activeSessionId = newSession.id;
      } catch (err) {
        console.error("Failed to create chat:", err);
        sendingInProgressRef.current = false;
        return;
      }
    }

    const userMsg = await addMessage(activeSessionId, "user", question);
    const assistantPlaceholder = { id: "temp-ai", role: "assistant", content: "", isLoading: true, sources: [] };
    setMessages(prev => [...prev, userMsg, assistantPlaceholder]);
    setInputValue("");
    setIsSending(true);

    if (messages.length === 0) {
      generateChatTitle(question).then(newTitle => {
        setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, title: newTitle } : s));
        updateSessionTitle(activeSessionId, newTitle);
      });
    }

    // --- HYBRID MEMORY: fetch facts for this session -----------------------
    let sessionFacts = [];
    try {
      sessionFacts = await getSessionFacts(activeSessionId);
    } catch (err) {
      console.warn("[app] Could not fetch session facts:", err);
    }

    // --- RECENCY WINDOW ----------------------------------------------------
    let historyPayload = [];
    if (messages.length <= (SESSION_OPENING + RECENT_WINDOW)) {
      historyPayload = messages;
    } else {
      const opening = messages.slice(0, SESSION_OPENING);
      const recent = messages.slice(-RECENT_WINDOW);
      historyPayload = [...opening, ...recent];
    }

    const chatHistory = historyPayload.map(m => ({
      role: m.role,
      content: m.content
    }));

    if (sessionFacts.length > 0) {
      const factsText = sessionFacts.map(f => `- ${f.fact_text}`).join("\n");
      chatHistory.unshift({
        role: "system",
        content: `[SESSION FACTS — durable details about the user's firm, extracted from earlier in this conversation. Use these to personalize answers, e.g. "since you're a Custody provider...". Do NOT repeat them back verbatim unless relevant.]\n${factsText}`
      });
    }

    try {
      let fullText = "";
      let receivedSources = [];

      await streamChat(
        question, 
        selectedJurisdiction,
        chatHistory,
        (textChunk) => {
          fullText += textChunk;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { ...updated[updated.length - 1], content: fullText };
            return updated;
          });
        },
        (sourcesData) => {
          receivedSources = sourcesData;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { ...updated[updated.length - 1], sources: sourcesData };
            return updated;
          });
        }
      );

      const finalAiMsg = await addMessage(activeSessionId, "assistant", fullText, receivedSources);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { ...updated[updated.length - 1], id: finalAiMsg.id, isLoading: false };
        return updated;
      });

      // Fire-and-forget fact extraction.
      extractFacts(activeSessionId, question)
        .then(newFacts => {
          if (newFacts && newFacts.length > 0) {
            saveSessionFacts(activeSessionId, newFacts);
          }
        })
        .catch(err => console.warn("[app] Fact extraction failed:", err));

    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: `⚠️ ${err.message || "Something went wrong."}`, isLoading: false };
        return updated;
      });
    } finally {
      justSentRef.current = true;
      sendingInProgressRef.current = false;
      setIsSending(false);
    }
  }, [inputValue, isSending, selectedJurisdiction, currentSessionId, messages]);

  return (
    <div className="h-full flex bg-luxury font-sans">
      <Sidebar 
        sessions={sessions} 
        currentSessionId={currentSessionId} 
        onSelectSession={handleSelectSession} 
        onNewChat={handleNewChat} 
        onRename={handleRename} 
        onDelete={handleDelete} 
        onTogglePin={handleTogglePin} 
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0 bg-luxury-light">
        <header className="bg-luxury border-b border-slate-800 px-4 sm:px-6 py-3 shrink-0 z-10 shadow-sm">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <button 
                onClick={() => setIsSidebarOpen(true)}
                className="md:hidden p-2 -ml-2 text-slate-400 hover:text-white transition-colors"
                aria-label="Open menu"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              </button>

              <div className="min-w-0 flex-1">
                <h1 className="text-base sm:text-lg font-semibold text-white truncate">
                  {currentSessionId 
                    ? sessions.find(s => s.id === currentSessionId)?.title || "New Conversation"
                    : "VARA Intelligence"}
                </h1>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  {currentSessionId ? "AI Regulatory Knowledge Base" : "Welcome"}
                </p>
              </div>
            </div>
            
            <div className="shrink-0">
              <JurisdictionSelector 
                options={jurisdictions} 
                value={selectedJurisdiction} 
                onChange={setSelectedJurisdiction} 
                disabled={isSending || jurisdictions.length === 0} 
              />
            </div>
          </div>
        </header>

        {loadError && (
          <div className="bg-red-900/50 border-b border-red-800 px-4 py-2 shrink-0">
            <div className="max-w-3xl mx-auto text-xs text-red-200">{loadError}</div>
          </div>
        )}

        <main className="flex-1 flex flex-col min-h-0 max-w-4xl mx-auto w-full">
          <ChatWindow 
            messages={messages} 
            onEdit={handleEditMessage} 
            isLoading={isLoadingMessages} 
          />
          <div className="w-full shrink-0">
            <ChatInput 
              value={inputValue} 
              onChange={setInputValue} 
              onSend={handleSend} 
              disabled={isSending || !selectedJurisdiction} 
            />
          </div>
        </main>
      </div>
    </div>
  );
}
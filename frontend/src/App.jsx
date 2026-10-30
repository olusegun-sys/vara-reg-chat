import { useEffect, useState, useCallback } from "react";
import JurisdictionSelector from "./components/JurisdictionSelector.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Sidebar from "./components/Sidebar.jsx";
import { getJurisdictions, streamChat, generateChatTitle } from "./api/client.js";
import { 
  getSessions, createSession, getMessages, addMessage, 
  updateSessionTitle, deleteSession, togglePin 
} from "./api/supabase.js";

// STRATEGY A (SMART WINDOW) CONFIG
const SESSION_OPENING = 2;
const RECENT_WINDOW = 8;

// localStorage key for session persistence across page reloads.
const SESSION_STORAGE_KEY = "vara_current_session_id";

export default function App() {
  const [jurisdictions, setJurisdictions] = useState([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const [sessions, setSessions] = useState([]);
  
  // Initialize from localStorage so refresh stays on the same session.
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    try {
      return localStorage.getItem(SESSION_STORAGE_KEY) || null;
    } catch {
      return null;
    }
  });
  
  const [messages, setMessages] = useState([]);
  
  // NEW: True while a session's messages are being fetched. Triggers the
  // loading spinner in ChatWindow and prevents the "jump-to-bottom" scroll
  // race that happens when an old session's messages appear all at once.
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    getJurisdictions().then(data => {
      setJurisdictions(data);
      if (data.length > 0) setSelectedJurisdiction(data[0].code);
    }).catch(err => setLoadError(err.message));
  }, []);

  useEffect(() => {
    getSessions().then(data => {
      setSessions(data);
      // Validate the stored session ID after sessions load.
      const stored = localStorage.getItem(SESSION_STORAGE_KEY);
      if (stored && !data.some(s => s.id === stored)) {
        console.warn("[app] Stored session ID not found, clearing.");
        localStorage.removeItem(SESSION_STORAGE_KEY);
        setCurrentSessionId(null);
      }
    }).catch(err => console.error("Error loading sessions:", err));
  }, []);

  // Persist currentSessionId to localStorage whenever it changes.
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
    if (isSending) return;

    // Show spinner while fetching. Cleared in .finally() regardless of outcome.
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

    let activeSessionId = currentSessionId;
    
    if (!activeSessionId) {
      try {
        const newSession = await createSession("New Conversation");
        setSessions(prev => [newSession, ...prev]);
        setCurrentSessionId(newSession.id);
        activeSessionId = newSession.id;
      } catch (err) {
        console.error("Failed to create chat:", err);
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

    // --- STRATEGY A: SMART WINDOW MEMORY SLICING ---
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

    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: `⚠️ ${err.message || "Something went wrong."}`, isLoading: false };
        return updated;
      });
    } finally {
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
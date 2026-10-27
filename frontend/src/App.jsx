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

export default function App() {
  const [jurisdictions, setJurisdictions] = useState([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);

  // Load jurisdictions on mount
  useEffect(() => {
    getJurisdictions().then(data => {
      setJurisdictions(data);
      if (data.length > 0) setSelectedJurisdiction(data[0].code);
    }).catch(err => setLoadError(err.message));
  }, []);

  // Load chat sessions from Supabase on mount
  useEffect(() => {
    getSessions().then(data => {
      setSessions(data);
      if (data.length > 0) {
        setCurrentSessionId(data[0].id);
      } else {
        handleNewChat();
      }
    }).catch(err => console.error("Error loading sessions:", err));
  }, []);

  // Load messages whenever the active session changes
  useEffect(() => {
    if (!currentSessionId) return;
    getMessages(currentSessionId).then(data => {
      setMessages(data.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sources: m.sources
      })));
    }).catch(err => console.error("Error loading messages:", err));
  }, [currentSessionId]);

  // --- Session Management Handlers ---
  const handleNewChat = async () => {
    try {
      const newSession = await createSession("New Conversation");
      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
      setInputValue("");
    } catch (err) {
      console.error("Failed to create chat:", err);
    }
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
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) setCurrentSessionId(remaining[0].id);
      else handleNewChat();
    }
    await deleteSession(id);
  };

  const handleTogglePin = async (id) => {
    const session = sessions.find(s => s.id === id);
    if (!session) return;
    const newPinnedState = !session.is_pinned;
    
    setSessions(prev => {
      const updated = prev.map(s => s.id === id ? { ...s, is_pinned: newPinnedState } : s);
      // Re-sort client side to match DB order
      return updated.sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return new Date(b.created_at) - new Date(a.created_at);
      });
    });
    await togglePin(id, newPinnedState);
  };

  // --- Edit & Send Handlers ---
  const handleEditMessage = (content) => {
    setInputValue(content);
  };

  const handleSend = useCallback(async () => {
    const question = inputValue.trim();
    if (!question || isSending || !selectedJurisdiction || !currentSessionId) return;

    // 1. Save user message to Supabase
    const userMsg = await addMessage(currentSessionId, "user", question);
    
    // 2. Add to UI immediately with a loading placeholder
    const assistantPlaceholder = { id: "temp-ai", role: "assistant", content: "", isLoading: true, sources: [] };
    setMessages(prev => [...prev, userMsg, assistantPlaceholder]);
    setInputValue("");
    setIsSending(true);

    // 3. Generate smart title in background if this is the first message
    if (messages.length === 0) {
      generateChatTitle(question).then(newTitle => {
        setSessions(prev => prev.map(s => s.id === currentSessionId ? { ...s, title: newTitle } : s));
        updateSessionTitle(currentSessionId, newTitle);
      });
    }

    // 4. Stream response from backend
    try {
      let fullText = "";
      let receivedSources = [];

      await streamChat(
        question, 
        selectedJurisdiction,
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

      // 5. Save final AI message to Supabase
      const finalAiMsg = await addMessage(currentSessionId, "assistant", fullText, receivedSources);
      
      // 6. Update UI with real DB ID
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
  }, [inputValue, isSending, selectedJurisdiction, currentSessionId, messages.length]);

  // Fallback if currentSessionId gets out of sync
  if (!currentSessionId && sessions.length > 0) {
    setCurrentSessionId(sessions[0].id);
  }

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
      />

      <div className="flex-1 flex flex-col min-w-0 bg-luxury-light">
        <header className="bg-luxury border-b border-slate-800 px-4 sm:px-6 py-4 shrink-0 z-10 shadow-sm">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-base sm:text-lg font-semibold text-white truncate md:hidden">
                VARA Intelligence
              </h1>
              <h1 className="text-base sm:text-lg font-serif text-white truncate hidden md:block">
                {sessions.find(s => s.id === currentSessionId)?.title || "VARA Intelligence"}
              </h1>
              <p className="text-xs text-slate-400 hidden sm:block">AI Regulatory Knowledge Base</p>
            </div>
            <JurisdictionSelector 
              options={jurisdictions} 
              value={selectedJurisdiction} 
              onChange={setSelectedJurisdiction} 
              disabled={isSending || jurisdictions.length === 0} 
            />
          </div>
        </header>

        {loadError && (
          <div className="bg-red-900/50 border-b border-red-800 px-4 py-2 shrink-0">
            <div className="max-w-3xl mx-auto text-xs text-red-200">{loadError}</div>
          </div>
        )}

        <main className="flex-1 flex flex-col min-h-0">
          <ChatWindow messages={messages} onEdit={handleEditMessage} />
          <div className="max-w-3xl mx-auto w-full shrink-0">
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
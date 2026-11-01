import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing Supabase environment variables");
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// Generate or retrieve a unique browser ID.
// Every person who opens the link sees their own private chat history.
function getBrowserId() {
  let id = localStorage.getItem("vara_browser_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("vara_browser_id", id);
  }
  return id;
}

const USER_ID = getBrowserId();

// --- Sessions CRUD ---------------------------------------------------------

export async function getSessions() {
  const { data, error } = await supabase
    .from("chat_sessions")
    .select("*")
    .eq("user_id", USER_ID)
    .order("is_pinned", { ascending: false })
    .order("created_at", { ascending: false });
    
  if (error) throw error;
  return data;
}

export async function createSession(title = "New Conversation") {
  const { data, error } = await supabase
    .from("chat_sessions")
    .insert([{ user_id: USER_ID, title }])
    .select()
    .single();
    
  if (error) throw error;
  return data;
}

export async function updateSessionTitle(sessionId, title) {
  const { error } = await supabase
    .from("chat_sessions")
    .update({ title })
    .eq("id", sessionId);
  if (error) throw error;
}

export async function deleteSession(sessionId) {
  const { error } = await supabase
    .from("chat_sessions")
    .delete()
    .eq("id", sessionId);
  if (error) throw error;
}

export async function togglePin(sessionId, isPinned) {
  const { error } = await supabase
    .from("chat_sessions")
    .update({ is_pinned: isPinned })
    .eq("id", sessionId);
  if (error) throw error;
}

// --- Messages CRUD ---------------------------------------------------------

export async function getMessages(sessionId) {
  const { data, error } = await supabase
    .from("chat_messages")
    .select("*")
    .eq("session_id", sessionId)
    .order("created_at", { ascending: true });
    
  if (error) throw error;
  return data;
}

export async function addMessage(sessionId, role, content, sources = []) {
  const { data, error } = await supabase
    .from("chat_messages")
    .insert([{ session_id: sessionId, role, content, sources }])
    .select()
    .single();
    
  if (error) throw error;
  return data;
}

// --- User facts (hybrid memory) --------------------------------------------
// Facts are per-USER, not per-session. A Custody provider is a Custody provider
// across every conversation they start. Session-scoped facts would vanish when
// the user clicks "New Session" — which breaks the whole point of memory.
//
// Session_id is kept as an audit trail (which session the fact was extracted
// from) but is not used for scoping or filtering.

export async function getUserFacts() {
  const { data, error } = await supabase
    .from("session_facts")
    .select("fact_text, created_at")
    .eq("user_id", USER_ID)
    .order("created_at", { ascending: true });
  if (error) {
    console.error("[supabase] getUserFacts failed:", error);
    return [];
  }
  return data || [];
}

export async function saveUserFacts(sessionId, facts) {
  if (!facts || facts.length === 0) return;
  // Dedupe within the batch — extraction occasionally produces the same
  // fact twice from a single message.
  const unique = Array.from(new Set(facts));
  const rows = unique.map((fact_text) => ({
    user_id: USER_ID,
    session_id: sessionId || null,
    fact_text,
  }));
  const { error } = await supabase.from("session_facts").insert(rows);
  if (error) {
    console.error("[supabase] saveUserFacts failed:", error);
  }
}
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing Supabase environment variables");
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// Generate or retrieve a unique browser ID.
// This ensures every person who opens the link sees their own private chat history,
// not the history of the person who created the link.
function getBrowserId() {
  let id = localStorage.getItem("vara_browser_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("vara_browser_id", id);
  }
  return id;
}

const USER_ID = getBrowserId();

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
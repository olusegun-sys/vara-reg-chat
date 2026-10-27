import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing Supabase environment variables");
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// For this POC, we will use a hardcoded ID to tie sessions to this browser.
// When we add Auth later, we swap this for supabase.auth.getUser().
const GUEST_USER_ID = "guest-user-001";

export async function getSessions() {
  const { data, error } = await supabase
    .from("chat_sessions")
    .select("*")
    .eq("user_id", GUEST_USER_ID)
    .order("is_pinned", { ascending: false })
    .order("created_at", { ascending: false });
    
  if (error) throw error;
  return data;
}

export async function createSession(title = "New Conversation") {
  const { data, error } = await supabase
    .from("chat_sessions")
    .insert([{ user_id: GUEST_USER_ID, title }])
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

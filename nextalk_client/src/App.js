import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import { v4 as uuidv4 } from "uuid";

/*
  Notes:
    - Backend endpoints used:
        POST  /api/chat/                          (body: { session_id, message, user_profile_id? })
        GET   /api/session/{session_id}/messages/ (returns short-term history list)
        GET   /api/memory/{user_profile_id}/      (returns long-term memories)
        POST  /api/memory/{user_profile_id}/      (create memory: body should match serializer)
    - Env override: REACT_APP_BACKEND_URL (defaults to http://localhost:8000)
*/

const BACKEND_BASE =
  process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const ENDPOINTS = {
  chat: `${BACKEND_BASE}/api/chat/`,
  sessionMessages: (sid) => `${BACKEND_BASE}/api/session/${sid}/messages/`,
  memories: (userProfileId) => `${BACKEND_BASE}/api/memory/${userProfileId}/`,
};

function Avatar({ role }) {
  if (role === "user") {
    return (
      <div className="avatar user-avatar" aria-hidden>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-4 0-8 2-8 4v2h16v-2c0-2-4-4-8-4z" />
        </svg>
      </div>
    );
  }
  return (
    <div className="avatar assistant-avatar" aria-hidden>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm1 14h-2v-2h2v2zm0-4h-2V6h2v6z" />
      </svg>
    </div>
  );
}

function useAutoScroll(messages, isTyping) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isTyping]);
  return ref;
}

export default function App() {
  // store message objects: { id, role, content, ts }
  const [messages, setMessages] = useState(() => {
    // load last open session messages lazily after mount
    return [
      {
        id: uuidv4(),
        role: "assistant",
        content: "Hello! How can I help you today?",
        ts: new Date().toISOString(),
      },
    ];
  });

  const [text, setText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);

  // Sidebar state
  const [conversations, setConversations] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("nt_conversations") || "[]");
    } catch {
      return [];
    }
  });
  const [activeSessionId, setActiveSessionId] = useState(() => {
    return localStorage.getItem("chat_session_id") || null;
  });

  // user profile id for long-term memories (optional)
  const [userProfileId, setUserProfileId] = useState(
    () => localStorage.getItem("nt_user_profile") || ""
  );

  // saved long-term memories list
  const [memories, setMemories] = useState([]);

  const textareaRef = useRef(null);
  const timeoutRef = useRef(null);
  const listRef = useAutoScroll(messages, isTyping);

  useEffect(() => {
    // persist conversations
    localStorage.setItem("nt_conversations", JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    if (!activeSessionId) {
      // create a default session if none
      const newId = uuidv4();
      const label = "Conversation 1";
      const entry = { id: newId, label, created: new Date().toISOString() };
      setConversations((c) => [entry, ...c]);
      setActiveSessionId(newId);
      localStorage.setItem("chat_session_id", newId);
      return;
    }
    // load short-term messages for this session
    loadSessionMessages(activeSessionId);
  }, []); // run once on mount

  useEffect(() => {
    // when activeSessionId changes persist and load messages
    if (!activeSessionId) return;
    localStorage.setItem("chat_session_id", activeSessionId);
    loadSessionMessages(activeSessionId);
    // fetch memories for userProfileId if present
    if (userProfileId) fetchMemories(userProfileId);
  }, [activeSessionId]);

  useEffect(() => {
    // persist userProfile choice
    if (userProfileId) localStorage.setItem("nt_user_profile", userProfileId);
  }, [userProfileId]);

  // auto-resize
  const resizeTextarea = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 220) + "px";
  };
  useEffect(() => resizeTextarea(), [text]);

  const loadSessionMessages = async (sessionId) => {
    if (!sessionId) return;
    try {
      const res = await fetch(ENDPOINTS.sessionMessages(sessionId));
      if (!res.ok) {
        // backend might return 404 or 500, handle gracefully
        setMessages([
          {
            id: uuidv4(),
            role: "assistant",
            content: "Session created. Say hello!",
            ts: new Date().toISOString(),
          },
        ]);
        return;
      }
      const data = await res.json();
      // expected data is an array of { role, text, ts }
      const normalized = (data || []).map((m, i) => ({
        id:
          m.id || `${sessionId}-${i}-${Math.random().toString(36).slice(2, 8)}`,
        role: m.role || "user",
        content: m.text || m.content || "",
        ts: m.ts || new Date().toISOString(),
      }));
      if (normalized.length === 0) {
        setMessages([
          {
            id: uuidv4(),
            role: "assistant",
            content: "Session ready. Ask me anything.",
            ts: new Date().toISOString(),
          },
        ]);
      } else {
        setMessages(normalized);
      }
    } catch (e) {
      console.error("Failed to load session messages", e);
      setMessages([
        {
          id: uuidv4(),
          role: "assistant",
          content: "Offline: cannot load session messages.",
          ts: new Date().toISOString(),
        },
      ]);
    }
  };

  const fetchMemories = async (profileId) => {
    if (!profileId) {
      setMemories([]);
      return;
    }
    try {
      const res = await fetch(ENDPOINTS.memories(profileId));
      if (!res.ok) {
        setMemories([]);
        return;
      }
      const data = await res.json();
      // data expected: list of memory objects with .content, .created_at etc.
      setMemories(data);
    } catch (e) {
      console.error("Failed to fetch memories", e);
      setMemories([]);
    }
  };

  const formatTimestamp = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  const wordDelay = (word) => {
    const base = 70;
    if (/[,;:]$/.test(word)) return base + 60;
    if (/[.!?]$/.test(word)) return base + 180;
    return base;
  };

  const streamAssistantMessage = (fullText) => {
    setIsTyping(true);
    setError(null);
    const words = fullText.split(/\s+/);
    const messageId = uuidv4();
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "assistant",
        content: "",
        ts: new Date().toISOString(),
      },
    ]);

    let i = 0;
    const step = () => {
      i++;
      setMessages((prev) => {
        const updated = [...prev];
        const lastIndex = updated.findIndex((m) => m.id === messageId);
        if (lastIndex >= 0) {
          updated[lastIndex] = {
            ...updated[lastIndex],
            content: words.slice(0, i).join(" "),
            ts: updated[lastIndex].ts || new Date().toISOString(),
          };
        }
        return updated;
      });
      if (i < words.length) {
        const delay = wordDelay(words[i - 1] || "");
        timeoutRef.current = setTimeout(step, delay);
      } else {
        setIsTyping(false);
        // after finished, store short-term message by hitting backend chat endpoint? backend already stores
      }
    };

    timeoutRef.current = setTimeout(step, 120);
  };

  useEffect(() => {
    return () => clearTimeout(timeoutRef.current);
  }, []);

  const sendMessage = async () => {
    if (!text.trim() || isTyping) return;
    const userText = text.trim();
    // ensure session id exists
    let sid = activeSessionId;
    if (!sid) {
      sid = uuidv4();
      setActiveSessionId(sid);
      setConversations((prev) => [
        {
          id: sid,
          label: "New Conversation",
          created: new Date().toISOString(),
        },
        ...prev,
      ]);
    }

    // optimistic add user message
    const userMsg = {
      id: uuidv4(),
      role: "user",
      content: userText,
      ts: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setText("");
    setIsTyping(true);
    setError(null);

    // send to backend
    try {
      const payload = { session_id: sid, message: userText };
      if (userProfileId) payload.user_profile_id = userProfileId;

      const res = await fetch(ENDPOINTS.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const textErr = await res.text();
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            role: "assistant",
            content: "⚠️ Server error",
            ts: new Date().toISOString(),
          },
        ]);
        setError(`Server returned ${res.status}`);
        console.error("chat error", res.status, textErr);
        return;
      }

      const data = await res.json();
      const botText = data.response || data.reply || data.result || "";
      const saveSuggestion = data.save_suggestion || null;

      if (!botText) {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            role: "assistant",
            content: "⚠️ No response from server.",
            ts: new Date().toISOString(),
          },
        ]);
        return;
      }

      // if backend returned a short_history, we can sync local messages (optional)
      if (Array.isArray(data.short_history)) {
        // convert and set messages to short_history (keeps server as source of truth)
        const normalized = data.short_history.map((m, i) => ({
          id: `${sid}-${i}-${Math.random().toString(36).slice(2, 8)}`,
          role: m.role || "user",
          content: m.text || "",
          ts: m.ts || new Date().toISOString(),
        }));
        setMessages(normalized);
      } else {
        // stream the assistant content
        streamAssistantMessage(botText);
      }

      // if backend suggested saving memory, show a quick UI affordance in sidebar
      if (saveSuggestion && saveSuggestion.suggest && userProfileId) {
        // show temporary action to save; we just push to memories locally to reflect change
        setMemories((prev) => [
          {
            id: `tmp-${Date.now()}`,
            content: saveSuggestion.example_save,
            created_at: new Date().toISOString(),
          },
          ...prev,
        ]);
      }
    } catch (e) {
      console.error("sendMessage failed", e);
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: "assistant",
          content: "⚠️ Network error",
          ts: new Date().toISOString(),
        },
      ]);
      setError("Network error — check backend.");
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // conversation management
  const createConversation = () => {
    const id = uuidv4();
    const label = `Conversation ${conversations.length + 1}`;
    const entry = { id, label, created: new Date().toISOString() };
    setConversations((prev) => [entry, ...prev]);
    setActiveSessionId(id);
  };
  const renameConversation = (id) => {
    const label = prompt("New name for conversation:");
    if (!label) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, label } : c))
    );
  };
  const deleteConversation = (id) => {
    if (
      // eslint-disable-next-line no-restricted-globals
      !confirm(
        "Delete this conversation locally? This will NOT delete server memories."
      )
    )
      return;
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeSessionId === id) {
      const next = conversations.find((c) => c.id !== id);
      const nid = next ? next.id : null;
      setActiveSessionId(nid);
      if (nid) localStorage.setItem("chat_session_id", nid);
    }
  };

  // save long-term memory (POST)
  const saveMemory = async (content) => {
    if (!userProfileId) {
      alert("Set a User Profile ID (top-left) to save long-term memories.");
      return;
    }
    try {
      const payload = { content }; // adapt if serializer needs extra fields
      const res = await fetch(ENDPOINTS.memories(userProfileId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        alert("Failed to save memory");
        return;
      }
      const data = await res.json();
      setMemories((prev) => [data, ...prev]);
      alert("Saved to long-term memory");
    } catch (e) {
      console.error("saveMemory", e);
      alert("Network error");
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-brand">NexTalk</div>
          <div className="profile-row">
            <input
              className="profile-input"
              placeholder="user_profile_id (optional)"
              value={userProfileId}
              onChange={(e) => setUserProfileId(e.target.value)}
              onBlur={() => {
                if (userProfileId) fetchMemories(userProfileId);
              }}
            />
            <button
              className="ghost small"
              onClick={() => {
                setUserProfileId("");
                setMemories([]);
                localStorage.removeItem("nt_user_profile");
              }}
            >
              Clear
            </button>
          </div>
        </div>

        <div className="conversations">
          <div className="conversations-header">
            <strong>Conversations</strong>
            <button className="ghost small" onClick={createConversation}>
              New
            </button>
          </div>
          <div className="conversations-list">
            {conversations.length === 0 && (
              <div className="muted">No local conversations yet</div>
            )}
            {conversations.map((c) => (
              <div
                key={c.id}
                className={`conv-item ${
                  c.id === activeSessionId ? "active" : ""
                }`}
              >
                <div
                  onClick={() => setActiveSessionId(c.id)}
                  className="conv-label"
                >
                  {c.label}
                </div>
                <div className="conv-actions">
                  <button
                    className="tiny"
                    onClick={() => renameConversation(c.id)}
                  >
                    ✎
                  </button>
                  <button
                    className="tiny"
                    onClick={() => deleteConversation(c.id)}
                  >
                    🗑
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="memories-section">
            <div className="mem-header">
              <strong>Saved Memories</strong>
              <button
                className="ghost small"
                onClick={() =>
                  userProfileId
                    ? fetchMemories(userProfileId)
                    : alert("Set user_profile_id")
                }
              >
                Refresh
              </button>
            </div>

            {memories.length === 0 && (
              <div className="muted">No long-term memories loaded</div>
            )}

            <div className="mem-list">
              {memories.map((m) => (
                <div
                  className="mem-item"
                  key={m.id || m.created_at || Math.random()}
                >
                  <div className="mem-content">
                    {m.content || m.text || m.summary || JSON.stringify(m)}
                  </div>
                  <div className="mem-actions">
                    <button
                      className="tiny"
                      title="Insert memory into chat"
                      onClick={() =>
                        setText((t) =>
                          t
                            ? t + " " + (m.content || m.text)
                            : m.content || m.text
                        )
                      }
                    >
                      ➕
                    </button>
                    <button
                      className="tiny"
                      title="Save again (create new)"
                      onClick={() => saveMemory(m.content || m.text)}
                    >
                      Save
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <small className="muted">
            Local only: conversations are saved in browser localStorage.
          </small>
        </div>
      </aside>

      <main className="main-area">
        <div className="topbar">
          <div className="title">NexTalk</div>
          <div className="top-actions">
            <div className="session-id">
              Session:{" "}
              <span className="muted">
                {activeSessionId?.slice(0, 8) || "—"}
              </span>
            </div>
          </div>
        </div>

        <div className="chat-window">
          <div className="messages" ref={listRef}>
            {messages.map((m) => (
              <div
                key={m.id}
                className={`message-row ${
                  m.role === "user" ? "row-user" : "row-assistant"
                }`}
              >
                <Avatar role={m.role} />
                <div
                  className={`bubble ${
                    m.role === "user" ? "bubble-user" : "bubble-assistant"
                  }`}
                >
                  <div className="bubble-content">{m.content}</div>
                  <div className="bubble-meta">
                    <span className="ts">{formatTimestamp(m.ts)}</span>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="message-row row-assistant typing-row">
                <Avatar role="assistant" />
                <div className="bubble bubble-assistant typing-bubble">
                  <div className="typing-dots" aria-hidden>
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}

            <div style={{ height: 18 }} />
          </div>

          <div className="composer">
            {error && <div className="error-banner">{error}</div>}
            <textarea
              ref={textareaRef}
              className="composer-input"
              placeholder="Type your message and press Enter to send..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
            />
            <button
              className="send"
              onClick={sendMessage}
              disabled={isTyping || !text.trim()}
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="currentColor"
                aria-hidden
              >
                <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

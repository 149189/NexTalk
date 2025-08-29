import React, { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello! How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      const data = await response.json();
      const botMessage = data.response || "⚠️ No response";

      // Stream word-by-word
      streamAssistantMessage(botMessage);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Backend error" },
      ]);
      setIsTyping(false);
    }
  };

  const streamAssistantMessage = (fullText) => {
    let words = fullText.split(" ");
    let index = 0;
    const newMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, newMessage]);

    const interval = setInterval(() => {
      index++;
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...newMessage,
          content: words.slice(0, index).join(" "),
        };
        return updated;
      });

      if (index >= words.length) {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, 150); // ms per word
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-bubble ${
              msg.role === "user" ? "user" : "assistant"
            }`}
          >
            {msg.content}
          </div>
        ))}
        {isTyping && (
          <div className="typing-indicator">Assistant is typing...</div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Send a message..."
        />
        <button onClick={sendMessage} disabled={isTyping}>
          {isTyping ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default App;

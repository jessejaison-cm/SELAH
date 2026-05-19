import React, { useState, useRef, useEffect } from "react";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const bottomRef = useRef(null);

  const sendMessage = async () => {
  if (!input.trim()) return;

  const userMessage = { sender: "user", text: input };
  setMessages((prev) => [...prev, userMessage]);
  setInput("");
  setIsTyping(true);

  try {
    const res = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage.text }),
    });

    const data = await res.json();

    const selahMessage = { sender: "selah", text: data.response };

    setMessages((prev) => [...prev, selahMessage]);
  } catch (err) {
    setMessages((prev) => [
      ...prev,
      { sender: "selah", text: "Server connection failed." },
    ]);
  }

  setIsTyping(false);
  };

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
  <div
    style={{
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      backgroundColor: "#f4f6f8",
      fontFamily: "sans-serif",
    }}
  >
    {/* Header */}
  <div
  style={{
    padding: "15px",
    backgroundColor: darkMode ? "#111827" : "#1f2937",
    color: "white",
    fontSize: "18px",
    fontWeight: "bold",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  }}
>
  <span>SELAH AI</span>

  <button
    onClick={() => setDarkMode(!darkMode)}
    style={{
      padding: "6px 12px",
      borderRadius: "15px",
      border: "none",
      cursor: "pointer",
      backgroundColor: darkMode ? "#facc15" : "#374151",
      color: darkMode ? "black" : "white",
      fontSize: "12px",
    }}
  >
    {darkMode ? "Light Mode" : "Dark Mode"}
  </button>
  </div>

    {/* Chat Area */}
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: darkMode ? "#0f172a" : "#f4f6f8",
        color: darkMode ? "white" : "black",
        fontFamily: "sans-serif",
        transition: "all 0.3s ease",
      }}
    >
      {messages.map((msg, idx) => (
        <div
          key={idx}
          style={{
            display: "flex",
            justifyContent:
              msg.sender === "user" ? "flex-end" : "flex-start",
            marginBottom: "10px",
          }}
        >
          <div
            style={{
              backgroundColor:
                msg.sender === "user" ? "#2563eb" : "#e5e7eb",
              color: msg.sender === "user" ? "white" : "black",
              padding: "10px 15px",
              borderRadius: "18px",
              maxWidth: "60%",
              fontSize: "14px",
            }}
          >
            {msg.text}
          </div>
        </div>
      ))}

      {isTyping && (
        <div style={{ marginBottom: "10px" }}>
          <div
            style={{
              backgroundColor: "#e5e7eb",
              padding: "10px 15px",
              borderRadius: "18px",
              fontStyle: "italic",
              maxWidth: "120px",
            }}
          >
            SELAH is typing...
          </div>
        </div>
      )}

      <div ref={bottomRef}></div>
    </div>

    {/* Input Area */}
    <div
      style={{
        padding: "15px",
        borderTop: "1px solid #ddd",
        display: "flex",
        gap: "10px",
        backgroundColor: "white",
      }}
    >
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            sendMessage();
          }
        }}
        placeholder="Type a message..."
        style={{
          flex: 1,
          padding: "12px",
          borderRadius: "20px",
          border: "1px solid #ccc",
          outline: "none",
        }}
      />
      <button
        onClick={sendMessage}
        style={{
          padding: "12px 18px",
          borderRadius: "20px",
          border: "none",
          backgroundColor: "#2563eb",
          color: "white",
          cursor: "pointer",
          fontWeight: "bold",
        }}
      >
        Send
      </button>
    </div>
  </div>
);
}

export default App;
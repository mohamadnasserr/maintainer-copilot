import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { MessageCircle, Send, X } from "lucide-react";
import "./styles.css";

declare global {
  interface Window {
    __MAINTAINERS_COPILOT_WIDGET_ID__?: string;
  }
}

type WidgetConfig = {
  widget_id: string;
  theme: { primary: string; position: string };
  greeting: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

function App() {
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [loading, setLoading] = useState(false);

  const widgetId = window.__MAINTAINERS_COPILOT_WIDGET_ID__ || "local-pandas";
  const conversationId = `widget-${widgetId}`;
  useEffect(() => {
    fetch(`http://localhost:8000/widget/${widgetId}/config`)
      .then((response) => response.json())
      .then(setConfig)
      .catch(() => {
        setConfig({
          widget_id: widgetId,
          theme: { primary: "#0f766e", position: "bottom-right" },
          greeting: "Ask about pandas maintenance, docs, and resolved issues.",
        });
      });
  }, [widgetId]);

  useEffect(() => {
    window.parent.postMessage(
      { type: "maintainers-copilot:resize", height: open ? 560 : 72 },
      "*",
    );
  }, [open]);

  async function send() {
    const trimmed = message.trim();

    if (!trimmed || loading) return;

    setMessages((previous) => [
      ...previous,
      { role: "user", content: trimmed },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          widget_id: widgetId,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat API returned ${response.status}`);
      }

      const data = await response.json();

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer || "I could not generate an answer.",
        },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: `Chat request failed: ${String(error)}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      send();
    }
  }

  const primary = config?.theme.primary || "#0f766e";

  if (!open) {
    return (
      <button
        className="bubble"
        style={{ backgroundColor: primary }}
        onClick={() => setOpen(true)}
        title="Open chat"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  return (
    <section className="panel">
      <header style={{ backgroundColor: primary }}>
        <strong>Maintainers Copilot</strong>
        <button onClick={() => setOpen(false)} title="Close chat">
          <X size={18} />
        </button>
      </header>

      <main>
        <p className="greeting">
          {config?.greeting || "Ask about pandas maintenance, docs, and resolved issues."}
        </p>

        {messages.map((chatMessage, index) => (
          <p key={index} className={chatMessage.role === "user" ? "user-message" : "answer"}>
            <strong>{chatMessage.role === "user" ? "You" : "Copilot"}:</strong>{" "}
            {chatMessage.content}
          </p>
        ))}

        {loading && <p className="answer">Searching pandas maintainer context...</p>}
      </main>

      <footer>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about pandas..."
          disabled={loading}
        />
        <button
          onClick={send}
          style={{ backgroundColor: primary }}
          title="Send message"
          disabled={loading}
        >
          <Send size={18} />
        </button>
      </footer>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
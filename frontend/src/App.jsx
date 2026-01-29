import { useMemo, useState } from "react";

const API_URL =
  __KACHNA_API_URL__ ??
  import.meta.env.VITE_API_URL ??
  "http://api.kachna.hobrasoft.cz";

const initialMessages = [
  {
    role: "assistant",
    content: "Ahoj, jsem Kachna. Co chceš vědět?",
  },
];

function ChatMessage({ role, content }) {
  return (
    <div className={`message message--${role}`}>
      <div className="message__role">{role}</div>
      <div className="message__content">{content}</div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const headerTitle = useMemo(() => "Kachna", []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading) {
      return;
    }

    const nextMessages = [
      ...messages,
      { role: "user", content: input.trim() },
    ];

    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "llama-local-7b",
          messages: nextMessages,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage = data.choices?.[0]?.message;

      setMessages((current) =>
        assistantMessage
          ? [...current, assistantMessage]
          : current,
      );
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `Chyba: ${error.message}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app__header">
        <h1>{headerTitle}</h1>
        <span>LLM UI</span>
      </header>

      <main className="app__chat">
        {messages.map((message, index) => (
          <ChatMessage
            key={`${message.role}-${index}`}
            role={message.role}
            content={message.content}
          />
        ))}
        {isLoading && (
          <div className="message message--assistant">
            <div className="message__role">assistant</div>
            <div className="message__content">Přemýšlím…</div>
          </div>
        )}
      </main>

      <form className="app__composer" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Napiš zprávu…"
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        <button type="submit" disabled={isLoading}>
          Odeslat
        </button>
      </form>
    </div>
  );
}

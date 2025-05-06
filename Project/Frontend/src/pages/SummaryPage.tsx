import React, { useState, useRef, useEffect } from "react";
import QuestionTemplates from "../components/QuestionTemplates"; // adjust path as needed

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: string[];
};

interface SummaryPageProps {
  chat: Chat;
  selectedModel: string;
  onUpdateMessages: (message: string) => void;
}

const SummaryPage: React.FC<SummaryPageProps> = ({
  chat,
  selectedModel,
  onUpdateMessages,
}) => {
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionKey, setSessionKey] = useState<string | null>(null);
  const [realTimeCrawlingEnabled, setRealTimeCrawlingEnabled] = useState(false); // NEW
  const [showTemplates, setShowTemplates] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // topics per platform
  const topicsByPlatform: Record<string, string[]> = {
    "Stack Overflow": ["JavaScript", "React", "CSS", "TypeScript"],
    Reddit: ["Academic", "Community", "Career"],
    "Red Note": ["Travel", "Food", "Fashion"],
  };

  // topic selection
  const [topic, setTopic] = useState("");
  useEffect(() => {
    setTopic("");
  }, [chat.platform, chat.topic]);

  // fetch or reuse sessionKey
  useEffect(() => {
    const storageKey = `sessionKey-${chat.id}`;
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      setSessionKey(stored);
    } else {
      fetch("http://127.0.0.1:8000/sessionKey/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chat.id }),
      })
        .then((res) => {
          if (!res.ok)
            throw new Error(`Error fetching session key: ${res.status}`);
          return res.json();
        })
        .then(({ session_id }) => {
          localStorage.setItem(storageKey, session_id);
          setSessionKey(session_id);
        })
        .catch((e) => {
          console.error(e);
          setError("Failed to get session key.");
        });
    }
  }, [chat.id]);

  // auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [chat.messages]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setSearchText(e.target.value);
  const handleTopicChange = (e: React.ChangeEvent<HTMLSelectElement>) =>
    setTopic(e.target.value);

  // NEW: a tiny toggle button component
  const RealTimeToggle = () => (
    <button
      type="button"
      onClick={() => setRealTimeCrawlingEnabled((f) => !f)}
      style={{
        padding: "6px 12px",
        marginBottom: "12px",
        borderRadius: "4px",
        border: "1px solid #188a8d",
        background: realTimeCrawlingEnabled ? "#188a8d" : "white",
        color: realTimeCrawlingEnabled ? "white" : "#188a8d",
        cursor: "pointer",
      }}
      aria-pressed={realTimeCrawlingEnabled}
    >
      {realTimeCrawlingEnabled ? "Real-time Crawl: On" : "Real-time Crawl: Off"}
    </button>
  );

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    onUpdateMessages(
      `<div class="user-message">User: ${searchText}</div>`
    );

    try {
      const normalizedSource = chat.platform.toLowerCase().replace(/\s/g, "");
      const requestBody = {
        search_query: searchText,
        llm_model: selectedModel,
        source: normalizedSource,
        chosen_topic: topic,
        session_id: sessionKey,
        real_time_crawling_enabled: realTimeCrawlingEnabled, // ← sent here
      };

      const res = await fetch("http://127.0.0.1:8000/search/", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      onUpdateMessages(
        `<div class="bot-message">Bot: ${data.result}</div>`
      );
    } catch (e: any) {
      console.error(e);
      setError("Failed to fetch result");
    } finally {
      setLoading(false);
      setSearchText("");
    }
  };

  const handleTemplateSelect = (template: string) => {
    const m = template.match(/_+/);
    const pos = m?.index ?? 0;
    const cleaned = template.replace(/_+/, "");
    setSearchText(cleaned);
    setShowTemplates(false);
    setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.setSelectionRange(pos, pos);
    }, 0);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100%",
        padding: "20px",
        boxSizing: "border-box",
      }}
    >
      <h2>
        Chat for {chat.platform} - {topic || "No Topic Selected"}
      </h2>

      {/* Topic selector */}
      <div style={{ marginBottom: "10px", width: "100%" }}>
        <label htmlFor="topic-select" style={{ marginRight: "10px" }}>
          Topic:
        </label>
        <select
          id="topic-select"
          value={topic}
          onChange={handleTopicChange}
          style={{
            padding: "5px",
            borderRadius: "5px",
            border: "1px solid #ccc",
            width: "100%",
          }}
        >
          <option value="">Select a Topic</option>
          {topicsByPlatform[chat.platform]?.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Real-time crawling toggle */}
      <RealTimeToggle />

      {/* Chat history + results */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid #ddd",
          padding: "10px",
          borderRadius: "8px",
          width: "100%",
          marginBottom: "10px",
        }}
      >
        {chat.messages.map((msg, i) => (
          <div
            key={i}
            id={`message-${i}`}
            dangerouslySetInnerHTML={{ __html: msg }}
          />
        ))}
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}
        <div ref={chatEndRef} />
      </div>

      {/* Templates popup */}
      {showTemplates && (
        <div style={{ marginBottom: "10px", width: "100%" }}>
          <QuestionTemplates
            platform={chat.platform}
            topic={topic}
            onTemplateSelect={handleTemplateSelect}
          />
        </div>
      )}

      {/* Fixed search bar */}
      <div style={{ borderTop: "1px solid #ddd", paddingTop: "10px" }}>
        <form
          onSubmit={handleSearchSubmit}
          style={{ display: "flex", alignItems: "center", width: "100%" }}
        >
          <input
            ref={inputRef}
            type="text"
            placeholder="Enter your question..."
            value={searchText}
            onChange={handleSearchChange}
            onFocus={() => setShowTemplates(true)}
            onBlur={() =>
              setTimeout(() => setShowTemplates(false), 150)
            }
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: "5px",
              border: "1px solid #ccc",
            }}
          />
          <button
            type="submit"
            style={{
              marginLeft: "10px",
              padding: "10px 20px",
              borderRadius: "5px",
              border: "none",
              backgroundColor: "#188a8d",
              color: "white",
              cursor: "pointer",
            }}
          >
            Search
          </button>
        </form>
      </div>
    </div>
  );
};

export default SummaryPage;

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

const SummaryPage: React.FC<SummaryPageProps> = ({ chat, selectedModel, onUpdateMessages }) => {
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Dictionary of possible topics for each platform
  const topicsByPlatform: Record<string, string[]> = {
    "Stack Overflow": ["JavaScript", "React", "CSS", "TypeScript"],
    Reddit: ["Academic", "Community", "Career"],
    "Red Note": ["Travel", "Food", "Fashion"],
  };

  // Topic state: initially empty (no default)
  const [topic, setTopic] = useState("");

  // Reset topic when chat changes
  useEffect(() => {
    setTopic("");
  }, [chat.platform, chat.topic]);

  // Auto-scroll effect: Scroll to the user message (if there are at least two messages)
  useEffect(() => {
    const messagesCount = chat.messages.length;
    if (messagesCount > 0) {
      // If there is a bot response, user message is at index messagesCount - 2; otherwise, index 0.
      const targetIndex = messagesCount > 1 ? messagesCount - 2 : 0;
      const element = document.getElementById(`message-${targetIndex}`);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }, [chat.messages]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
  };

  const handleTopicChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTopic(e.target.value);
  };

  const handleSearchSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Append user's query to chat history as HTML
    onUpdateMessages(`<div class="user-message">User: ${searchText}</div>`);
    console.log("Submitting query:", searchText);

    try {
      // Use dynamic values: normalized source and selected model
      const normalizedSource = chat.platform.toLowerCase().replace(/\s/g, "");
      const modelToSend = selectedModel;

      const response = await fetch("http://127.0.0.1:8000/search/", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search_query: searchText,
          llm_model: modelToSend,
          source: normalizedSource,
          chosen_topic: topic,
        }),
      });

      if (!response.ok) {
        throw new Error(`Network response was not ok, status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Received data:", data);

      // Append bot response as HTML to chat history
      onUpdateMessages(`<div class="bot-message">Bot: ${data.result}</div>`);
    } catch (err: any) {
      console.error("Error fetching search result:", err);
      setError("Failed to fetch result");
    } finally {
      setLoading(false);
      setSearchText("");
    }
  };

  const handleTemplateSelect = (template: string) => {
    const match = template.match(/_+/);
    let caretPosition = 0;
    if (match && match.index !== undefined) {
      caretPosition = match.index;
    }
    const cleanedTemplate = template.replace(/_+/, "");
    setSearchText(cleanedTemplate);
    setShowTemplates(false);
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.setSelectionRange(caretPosition, caretPosition);
      }
    }, 0);
  };

  // Local state for controlling template display
  const [showTemplates, setShowTemplates] = useState(false);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",   // Full viewport height
        width: "100%",     // Full width
        boxSizing: "border-box",
        padding: "20px",
      }}
    >
      <h2>
        Chat for {chat.platform} - {topic || "No Topic Selected"}
      </h2>

      {/* Topic Dropdown */}
      <div style={{ marginBottom: "10px", width: "100%" }}>
        <label htmlFor="topic-select" style={{ fontWeight: "bold", marginRight: "10px" }}>
          Topic:
        </label>
        <select
          id="topic-select"
          value={topic}
          onChange={handleTopicChange}
          style={{ padding: "5px", borderRadius: "5px", border: "1px solid #ccc", width: "100%" }}
        >
          <option value="">Select a Topic</option>
          {topicsByPlatform[chat.platform]?.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Unified Chat History */}
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
        {chat.messages.map((msg, index) => (
          <div key={index} id={`message-${index}`} dangerouslySetInnerHTML={{ __html: msg }} />
        ))}
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>

      {/* Question Templates (displayed above the search input) */}
      {showTemplates && (
        <div style={{ marginBottom: "10px", width: "100%" }}>
          <QuestionTemplates
            platform={chat.platform}
            topic={topic}
            onTemplateSelect={handleTemplateSelect}
          />
        </div>
      )}

      {/* Fixed Search Bar at the Bottom */}
      <div style={{ borderTop: "1px solid #ddd", paddingTop: "10px", width: "100%" }}>
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", alignItems: "center", width: "100%" }}>
          <input
            ref={inputRef}
            type="text"
            placeholder="Enter your question..."
            value={searchText}
            onChange={handleSearchChange}
            onFocus={() => setShowTemplates(true)}
            onBlur={() => setTimeout(() => setShowTemplates(false), 150)}
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: "5px",
              border: "1px solid #ccc",
              width: "100%",
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

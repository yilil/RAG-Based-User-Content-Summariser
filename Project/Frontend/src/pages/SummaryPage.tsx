import React, { useState, useRef, useEffect } from "react";
import QuestionTemplates from "../components/QuestionTemplates"; // adjust path as needed

const rawIp = import.meta.env.VITE_BASE_URL;

const BASE_URL = rawIp && rawIp.length > 0
  ? `http://${rawIp}:8000`
  : 'http://127.0.0.1:8000';

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
  const [realTimeCrawlingEnabled, setRealTimeCrawlingEnabled] = useState(false);
  const [mixedSearchEnabled, setMixedSearchEnabled] = useState(false);
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
      fetch(`${BASE_URL}/sessionKey/`, {
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
      onClick={() => {
        setRealTimeCrawlingEnabled((prev) => !prev);
        // 如果开启实时抓取，关闭混合搜索(互斥)
        if (!realTimeCrawlingEnabled) {
          setMixedSearchEnabled(false);
        }
      }}
      style={{
        padding: "6px 12px",
        marginRight: "10px",
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

  // 添加新的MixedSearchToggle组件
  const MixedSearchToggle = () => (
    <button
      type="button"
      onClick={() => {
        setMixedSearchEnabled((prev) => !prev);
        // 如果开启混合搜索，关闭实时抓取(互斥)
        if (!mixedSearchEnabled) {
          setRealTimeCrawlingEnabled(false);
        }
      }}
      style={{
        padding: "6px 12px",
        marginBottom: "12px",
        borderRadius: "4px",
        border: "1px solid #6a5acd",
        background: mixedSearchEnabled ? "#6a5acd" : "white",
        color: mixedSearchEnabled ? "white" : "#6a5acd",
        cursor: "pointer",
      }}
      aria-pressed={mixedSearchEnabled}
    >
      {mixedSearchEnabled ? "Mixed Search: On" : "Mixed Search: Off"}
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
      
      // 确定API端点
      let endpoint = `${BASE_URL}/search/`;
      
      // 如果开启了实时抓取，使用real_time_crawl端点
      if (realTimeCrawlingEnabled) {
        endpoint = `${BASE_URL}/real_time_crawl/`;
      } 
      // 如果开启了混合搜索，使用mix_search端点
      else if (mixedSearchEnabled) {
        endpoint = `${BASE_URL}/mix_search/`;
      }
      
      const requestBody = {
        search_query: searchText,
        llm_model: selectedModel,
        source: normalizedSource,
        chosen_topic: topic,
        session_id: sessionKey,
        // 仅在使用普通搜索时需要这个参数
        real_time_crawling_enabled: false
      };

      const res = await fetch(endpoint, {
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

      {/* 搜索选项区域 */}
      <div style={{ display: "flex", marginBottom: "10px" }}>
        <RealTimeToggle />
        <MixedSearchToggle />
      </div>

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

import React, { useState, useRef, useEffect } from "react";
import QuestionTemplates from "../components/QuestionTemplates"; // adjust path as needed

const rawIp = import.meta.env.VITE_BASE_URL;
const BASE_URL = rawIp && rawIp.length > 0
  ? `http://${rawIp}:8000`
  : 'http://127.0.0.1:8000';

type Message = {
  id: string;
  type: 'user' | 'bot';
  content: string;
  timestamp: string;
};

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: Message[];
};

interface SummaryPageProps {
  chat: Chat;
  selectedModel: string;
  onUpdateMessages: (message: Message | Message[]) => void;
  onSetMessages: (messages: Message[]) => void;
}

const SummaryPage: React.FC<SummaryPageProps> = ({
  chat,
  selectedModel,
  onUpdateMessages,
  onSetMessages,
}) => {
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionKey, setSessionKey] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [realTimeCrawlingEnabled, setRealTimeCrawlingEnabled] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load chat history from backend
  const loadChatHistory = async (sessionId: string) => {
    try {
      console.log(`Loading chat history for session: ${sessionId}`);
      const response = await fetch(`${BASE_URL}/getMemory/?session_id=${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch memory: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Memory data received:', data);
      
      if (data.memory && data.memory.length > 0) {
        // Convert backend JSON format to frontend Message format
        const messages: Message[] = [];
        data.memory.forEach((item: {user: string, ai: string}, index: number) => {
          // Create realistic timestamps for historical messages
          const baseTime = new Date();
          const userTime = new Date(baseTime.getTime() - (data.memory.length - index) * 120000); // 2 minutes apart
          const botTime = new Date(baseTime.getTime() - (data.memory.length - index) * 120000 + 60000); // 1 minute after user
          
          messages.push({
            id: `${sessionId}-history-user-${index}`,
            type: 'user',
            content: item.user,
            timestamp: userTime.toISOString(),
          });
          
          messages.push({
            id: `${sessionId}-history-bot-${index}`,
            type: 'bot',
            content: item.ai,
            timestamp: botTime.toISOString(),
          });
        });
        
        console.log('Formatted messages:', messages);
        // Replace current messages with historical messages
        onSetMessages(messages);
      }
      setHistoryLoaded(true);
    } catch (error) {
      console.error('Failed to load chat history:', error);
      setHistoryLoaded(true); // Still mark as loaded to prevent retry loops
    }
  };

  // topics per platform
  const topicsByPlatform: Record<string, string[]> = {
    "Stack Overflow": ["JavaScript", "React", "CSS", "TypeScript"],
    Reddit: ["Academic", "Community", "Career"],
    "Red Note": ["Travel", "Food", "Fashion"],
  };

  // Reset history loaded state when chat changes
  useEffect(() => {
    setHistoryLoaded(false);
  }, [chat.id]);

  // topic selection
  const [topic, setTopic] = useState("");
  useEffect(() => {
    setTopic("");
  }, [chat.platform, chat.topic]);

  // fetch or reuse sessionKey and load history
  useEffect(() => {
    const storageKey = `sessionKey-${chat.id}`;
    const stored = localStorage.getItem(storageKey);
    
    if (stored) {
      setSessionKey(stored);
      // Load history if we haven't loaded it yet and we have messages in chat
      if (!historyLoaded && chat.messages.length === 0) {
        loadChatHistory(stored);
      }
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
          // Load history for new session too
          if (!historyLoaded && chat.messages.length === 0) {
            loadChatHistory(session_id);
          }
        })
        .catch((e) => {
          console.error(e);
          setError("Failed to get session key.");
        });
    }
  }, [chat.id, historyLoaded, chat.messages.length]);

  // auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [chat.messages]);

  // Save session to backend
  const saveSession = async () => {
    if (!sessionKey || chat.messages.length === 0) {
      return;
    }

    try {
      console.log('Saving session...', sessionKey, chat.messages.length);
      const response = await fetch(`${BASE_URL}/saveSession/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionKey,
          messages: chat.messages,
          platform: chat.platform,
          topic: topic
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Session saved successfully:', data.message);
      } else {
        console.error('Failed to save session:', response.status);
      }
    } catch (error) {
      console.error('Error saving session:', error);
    }
  };

  // Auto-save session when messages change (with debounce)
  useEffect(() => {
    if (chat.messages.length > 0 && sessionKey) {
      const saveTimer = setTimeout(() => {
        saveSession();
      }, 2000); // Save after 2 seconds of inactivity

      return () => clearTimeout(saveTimer);
    }
  }, [chat.messages, sessionKey]);

  // Save session when component unmounts (user switches chat)
  useEffect(() => {
    return () => {
      if (sessionKey && chat.messages.length > 0) {
        // Use synchronous saving when component unmounts
        fetch(`${BASE_URL}/saveSession/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionKey,
            messages: chat.messages,
            platform: chat.platform,
            topic: topic
          }),
          keepalive: true // Ensure request completes even if page unloads
        }).catch(error => {
          console.error('Error saving session on unmount:', error);
        });
      }
    };
  }, [sessionKey, chat.messages, chat.platform, topic]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setSearchText(e.target.value);
  const handleTopicChange = (e: React.ChangeEvent<HTMLSelectElement>) =>
    setTopic(e.target.value);

  // 新的药丸形状切换器组件
  const SearchModeToggle = () => {
    const getActiveMode = () => {
      if (realTimeCrawlingEnabled) return 'realtime';
      return 'standard';
    };

    const handleModeChange = (mode: string) => {
      switch (mode) {
        case 'realtime':
          setRealTimeCrawlingEnabled(true);
          break;
        case 'standard':
          setRealTimeCrawlingEnabled(false);
          break;
      }
    };

    const activeMode = getActiveMode();

    return (
      <div style={{
        position: 'relative',
        display: 'inline-flex',
        backgroundColor: '#f1f5f9',
        padding: '4px',
        borderRadius: '24px',
        border: '1px solid #e2e8f0',
        marginBottom: '12px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}>
        {/* 滑动指示器 */}
        <div
          style={{
            position: 'absolute',
            top: '4px',
            left: activeMode === 'realtime' ? '4px' : 'calc(50% + 2px)',
            width: 'calc(50% - 4px)',
            height: 'calc(100% - 8px)',
            backgroundColor: '#ffffff',
            borderRadius: '20px',
            transition: 'left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
            zIndex: 1,
          }}
        />
        
        {/* 按钮选项 */}
        <button
          type="button"
          onClick={() => handleModeChange('realtime')}
          style={{
            position: 'relative',
            zIndex: 2,
            padding: '8px 20px',
            border: 'none',
            background: 'transparent',
            borderRadius: '20px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: activeMode === 'realtime' ? '600' : '500',
            color: activeMode === 'realtime' ? '#188a8d' : '#64748b',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
            minWidth: '120px',
          }}
        >
          Real-time Crawl
        </button>
        
        <button
          type="button"
          onClick={() => handleModeChange('standard')}
          style={{
            position: 'relative',
            zIndex: 2,
            padding: '8px 20px',
            border: 'none',
            background: 'transparent',
            borderRadius: '20px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: activeMode === 'standard' ? '600' : '500',
            color: activeMode === 'standard' ? '#059669' : '#64748b',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
            minWidth: '120px',
          }}
        >
          Standard
        </button>
      </div>
    );
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // 创建用户消息对象
    const userMessage: Message = {
      id: Math.random().toString(36).substring(2, 15),
      type: 'user',
      content: searchText,
      timestamp: new Date().toISOString(),
    };

    onUpdateMessages(userMessage);

    try {
      const normalizedSource = chat.platform.toLowerCase().replace(/\s/g, "");
      
      // 确定API端点
      let endpoint = `${BASE_URL}/search/`;
      
      // 如果开启了实时抓取，使用real_time_crawl端点
      if (realTimeCrawlingEnabled) {
        endpoint = `${BASE_URL}/real_time_crawl/`;
      }
      
      const requestBody = {
        search_query: searchText,
        llm_model: selectedModel,
        source: normalizedSource,
        chosen_topic: topic,
        session_id: sessionKey,
        // 仅在使用普通搜索时需要这个参数
        real_time_crawling_enabled: realTimeCrawlingEnabled
      };

      const res = await fetch(endpoint, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      
      // 创建bot消息对象
      const botMessage: Message = {
        id: Math.random().toString(36).substring(2, 15),
        type: 'bot',
        content: data.result,
        timestamp: new Date().toISOString(),
      };

      onUpdateMessages(botMessage);
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

      {/* 搜索选项区域 - 使用新的药丸切换器 */}
      <div style={{ display: "flex", marginBottom: "10px", alignItems: "center" }}>
        <SearchModeToggle />
        <div style={{ 
          marginLeft: '12px', 
          fontSize: '12px', 
          color: '#6b7280',
          fontStyle: 'italic'
        }}>
          {realTimeCrawlingEnabled && "🔴 Real-time web crawling enabled"}
          {!realTimeCrawlingEnabled && "📊 Standard search mode"}
        </div>
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
            key={msg.id || i}
            id={`message-${i}`}
            style={{
              marginBottom: "10px",
              padding: "8px",
              borderRadius: "5px",
              backgroundColor: msg.type === 'user' ? "#f0f8ff" : "#f5f5f5",
            }}
          >
            <div style={{ 
              fontWeight: "bold", 
              marginBottom: "4px",
              color: msg.type === 'user' ? "#007bff" : "#333"
            }}>
              {msg.type === 'user' ? 'User' : 'Bot'}
            </div>
            <div 
              style={{ fontSize: "14px" }}
              dangerouslySetInnerHTML={{ __html: msg.content }}
            />
          </div>
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

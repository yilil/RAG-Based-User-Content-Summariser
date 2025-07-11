import React, { useState, useRef, useEffect } from "react";
import QuestionTemplates from "../components/QuestionTemplates"; // adjust path as needed
import TopBar from "../components/TopBar";

// Safe access to import.meta.env for compatibility with Jest
const getBaseUrl = () => {
  try {
    const rawIp = import.meta.env.VITE_BASE_URL;
    return rawIp && rawIp.length > 0
      ? `http://${rawIp}:8000`
      : 'http://127.0.0.1:8000';
  } catch (error) {
    // Fallback for test environment where import.meta is not available
    return process.env.VITE_BASE_URL 
      ? `http://${process.env.VITE_BASE_URL}:8000`
      : 'http://127.0.0.1:8000';
  }
};

const BASE_URL = getBaseUrl();

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
  createdAt: string;
};

interface SummaryPageProps {
  chat: Chat;
  selectedModel: string;
  onUpdateMessages: (message: Message | Message[]) => void;
  onSetMessages: (messages: Message[]) => void;
  onModelChange: (model: string) => void;
}

const SummaryPage: React.FC<SummaryPageProps> = ({
  chat,
  selectedModel,
  onUpdateMessages,
  onSetMessages,
  onModelChange,
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
    "Rednote": ["Travel", "Food", "Fashion"],
  };

  // Reset all component state when chat changes
  useEffect(() => {
    console.log(`Resetting state for chat change: ${chat.id}`);
    setHistoryLoaded(false);
    setSearchText("");
    setLoading(false);
    setError(null);
    setRealTimeCrawlingEnabled(false);
    setShowTemplates(false);
  }, [chat.id]);

  // topic selection
  const [topic, setTopic] = useState("");
  useEffect(() => {
    setTopic("");
  }, [chat.platform, chat.topic]);

  // fetch or reuse sessionKey - only run when chat.id changes
  useEffect(() => {
    // Check if this is a virtual chat from history session
    if (chat.id.startsWith('history-')) {
      const historySessionId = chat.id.replace('history-', '');
      console.log(`Using history session ID directly: ${historySessionId}`);
      setSessionKey(historySessionId);
      return;
    }

    // Regular session management for new chats
    const storageKey = `sessionKey-${chat.id}`;
    const stored = localStorage.getItem(storageKey);
    
    console.log(`Session effect triggered for chat ${chat.id}, stored:`, stored);
    
    if (stored) {
      setSessionKey(stored);
      console.log(`Using existing session key: ${stored}`);
    } else {
      console.log(`Creating new session for chat ${chat.id}`);
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
          console.log(`New session created: ${session_id}`);
        })
        .catch((e) => {
          console.error(e);
          setError("Failed to get session key.");
        });
    }
  }, [chat.id]); // Only depend on chat.id

  // Separate effect for loading history when sessionKey is ready
  useEffect(() => {
    // Only load history for non-virtual chats (regular chats that need backend history)
    // Virtual chats from history sessions already have their messages from getActiveChat()
    if (sessionKey && !historyLoaded && chat.messages.length === 0 && !chat.id.startsWith('history-')) {
      console.log(`Loading history for session: ${sessionKey}`);
      loadChatHistory(sessionKey);
    } else if (chat.id.startsWith('history-')) {
      // For virtual chats from history sessions, mark as loaded immediately
      // since messages are already provided by getActiveChat()
      console.log(`Virtual chat from history session - skipping backend history load`);
      setHistoryLoaded(true);
    } else if (sessionKey && !historyLoaded && chat.messages.length > 0) {
      // For chats that already have messages (e.g., converted from history sessions)
      // mark as loaded since they don't need backend history loading
      console.log(`Chat already has messages - marking history as loaded`);
      setHistoryLoaded(true);
    }
  }, [sessionKey, historyLoaded, chat.messages.length, chat.id]);

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
            backgroundColor: '#FAE9F4',
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
            color: activeMode === 'realtime' ? '#DA5AA0' : '#64748b',
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
            color: activeMode === 'standard' ? '#DA5AA0' : '#64748b',
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
    
    console.log('=== LOADING STATE DEBUG ===');
    console.log('Setting loading to true');
    console.log('Current sessionKey:', sessionKey);
    console.log('Chat ID:', chat.id);
    console.log('Chat ID starts with history:', chat.id.startsWith('history-'));
    
    setLoading(true);
    setError(null);

    // 检查sessionKey是否可用，对于历史session需要特殊处理
    let effectiveSessionKey = sessionKey;
    
    // 如果是历史session但sessionKey还没有设置，尝试从chat.id中获取
    if (chat.id.startsWith('history-') && !sessionKey) {
      const historySessionId = chat.id.replace('history-', '');
      console.log(`Deriving session key from history chat ID: ${historySessionId}`);
      effectiveSessionKey = historySessionId;
      // 同时更新sessionKey状态
      setSessionKey(historySessionId);
    }
    
    if (!effectiveSessionKey) {
      console.error('No session key available for search - setting loading to false');
      setError("Session not ready. Please try again.");
      setLoading(false);
      return;
    }
    
    console.log('Effective session key:', effectiveSessionKey);
    console.log('Session key is available, proceeding with search');
    console.log('=== LOADING STATE DEBUG END ===');

    console.log('=== SEARCH SUBMIT DEBUG ===');
    console.log('Chat ID:', chat.id);
    console.log('Session Key:', effectiveSessionKey);
    console.log('Search Text:', searchText);

    // 创建用户消息对象
    const userMessage: Message = {
      id: Math.random().toString(36).substring(2, 15),
      type: 'user',
      content: searchText,
      timestamp: new Date().toISOString(),
    };

    console.log('=== USER MESSAGE SUBMISSION ===');
    console.log('User message:', userMessage);
    console.log('Chat before adding message:', chat.id, 'Message count:', chat.messages.length);
    console.log('Adding user message via onUpdateMessages');
    onUpdateMessages(userMessage);
    
    console.log('User message sent to onUpdateMessages');

    // 给更多时间让状态更新，特别是当历史session转换为新chat时
    // 如果是历史session，转换过程需要更多时间
    const waitTime = chat.id.startsWith('history-') ? 500 : 100;
    console.log(`Waiting ${waitTime}ms for state updates to complete (history session: ${chat.id.startsWith('history-')})`);
    await new Promise(resolve => setTimeout(resolve, waitTime));
    console.log('=== USER MESSAGE SUBMISSION END ===');

    try {
      const normalizedSource = chat.platform.toLowerCase().replace(/\s/g, "");
      
      // 确定要使用的session ID - 如果是历史session转换的chat，使用localStorage中存储的值
      let effectiveSessionId = effectiveSessionKey;
      if (chat.id && !chat.id.startsWith('history-')) {
        const storedSessionId = localStorage.getItem(`sessionKey-${chat.id}`);
        if (storedSessionId) {
          effectiveSessionId = storedSessionId;
        }
      }
      
      console.log('Final Effective Session ID:', effectiveSessionId);
      
      // 再次检查是否有有效的session ID
      if (!effectiveSessionId) {
        console.error('No effective session ID available');
        setError("Session ID not available. Please try again.");
        setLoading(false);
        return;
      }
      
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
        session_id: effectiveSessionId,
        // 仅在使用普通搜索时需要这个参数
        real_time_crawling_enabled: realTimeCrawlingEnabled
      };

      console.log('=== API REQUEST DEBUG ===');
      console.log('Endpoint:', endpoint);
      console.log('Request Body:', JSON.stringify(requestBody, null, 2));

      const res = await fetch(endpoint, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      console.log('Response Status:', res.status);
      console.log('Response OK:', res.ok);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('Error Response:', errorText);
        throw new Error(`Status ${res.status}: ${errorText}`);
      }
      
      const data = await res.json();
      console.log('Response Data:', data);
      
      if (!data.result) {
        console.error('No result in response data');
        throw new Error('No result returned from server');
      }
      
      // 创建bot消息对象
      const botMessage: Message = {
        id: Math.random().toString(36).substring(2, 15),
        type: 'bot',
        content: data.result,
        timestamp: new Date().toISOString(),
      };

      console.log('Created bot message:', botMessage.id, 'Content length:', botMessage.content.length);
      console.log('Adding bot message via onUpdateMessages');
      onUpdateMessages(botMessage);
      console.log('Bot message sent to onUpdateMessages - addition complete');
      console.log('=== API REQUEST DEBUG END ===');
    } catch (e: any) {
      console.error('=== API REQUEST ERROR ===');
      console.error('Error object:', e);
      console.error('Error message:', e.message);
      console.error('Error stack:', e.stack);
      console.error('=== API REQUEST ERROR END ===');
      setError("Failed to fetch result: " + (e.message || 'Unknown error'));
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
        overflow: "hidden",
      }}
    >
      <TopBar 
        selectedModel={selectedModel}
        onModelChange={onModelChange}
      />
      
      <div style={{
        flex: 1,
        padding: "20px",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}>
        <h2 style={{ margin: "0 0 15px 0", flexShrink: 0 }}>
          Chat for {chat.platform} - {topic || "No Topic Selected"}
        </h2>

      {/* Topic selector */}
      <div style={{ marginBottom: "10px", flexShrink: 0 }}>
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
            boxSizing: "border-box",
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
          marginBottom: "10px",
          minHeight: 0, // 允许flex item收缩
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
              backgroundColor: msg.type === 'user' ? "#DFE0FF" : "#f5f5f5",
            }}
          >
            <div style={{ 
              fontWeight: "bold", 
              marginBottom: "4px",
              color: msg.type === 'user' ? "#5A33CF" : "#333"
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
      <div style={{ 
        borderTop: "1px solid #ddd", 
        paddingTop: "10px",
        flexShrink: 0 // 防止搜索栏被压缩
      }}>
        <form
          onSubmit={handleSearchSubmit}
          style={{ display: "flex", alignItems: "center", gap: "10px" }}
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
              padding: "10px 20px",
              borderRadius: "5px",
              border: "none",
              backgroundColor: "#188a8d",
              color: "white",
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            Search
          </button>
        </form>
      </div>
      </div>
    </div>
  );
};

export default SummaryPage;

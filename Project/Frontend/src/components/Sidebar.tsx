import React, { useState } from "react";

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

type HistorySession = {
  session_id: string;
  platform: string | null;
  topic: string | null;
  memory_data: Array<{user: string, ai: string}>;
  updated_at: string;
};

interface SidebarProps {
  chats: Chat[];
  historySessions: HistorySession[];
  activeChatId: string | null;
  activeHistorySessionId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onSelectHistorySession: (sessionId: string) => Promise<void>;
  onModelChange: (model: string) => void;
  onDeleteSession?: (sessionId: string) => Promise<void>;
}

const Sidebar: React.FC<SidebarProps> = ({
  chats,
  historySessions,
  activeChatId,
  activeHistorySessionId,
  onNewChat,
  onSelectChat,
  onSelectHistorySession,
  onModelChange,
  onDeleteSession,
}) => {
  const [selectedModel, setSelectedModel] = useState("gemini-2.0-flash");

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    onModelChange(newModel);
  };

  // Helper function to format session title
  const getSessionTitle = (session: HistorySession) => {
    if (session.memory_data && session.memory_data.length > 0) {
      const firstMessage = session.memory_data[0].user;
      return firstMessage.length > 35 
        ? firstMessage.substring(0, 35) + "..." 
        : firstMessage;
    }
    return `${session.platform || "Unknown"} Session`;
  };

  // Helper function to format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) {
      return "Today";
    } else if (diffDays === 2) {
      return "Yesterday";
    } else if (diffDays <= 7) {
      return `${diffDays - 1} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // Handle delete session
  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent selecting the session
    
    if (window.confirm('Are you sure you want to delete this chat?')) {
      if (onDeleteSession) {
        await onDeleteSession(sessionId);
      }
    }
  };

  // Combine current chats and history sessions for unified display
  const allChatItems = [
    // Current chats (only truly new chats from this session, not virtual chats from history)
    ...chats
      .filter(chat => !historySessions.some(session => session.session_id === chat.id))
      .map(chat => ({
        id: chat.id,
        type: 'current' as const,
        title: `${chat.platform} Chat`,
        subtitle: `${chat.messages.length} messages`,
        date: "Current session",
        isActive: activeChatId === chat.id
      })),
    // History sessions (show all history sessions, regardless of whether they're loaded as virtual chats)
    ...historySessions.map(session => ({
      id: session.session_id,
      type: 'history' as const,
      title: getSessionTitle(session),
      subtitle: `${session.platform || "Unknown"} • ${session.memory_data.length} messages`,
      date: formatDate(session.updated_at),
      // Check if this history session is currently active (either as activeHistorySessionId or as virtual chat)
      isActive: activeHistorySessionId === session.session_id || activeChatId === session.session_id
    }))
  ];

  const handleItemClick = (item: typeof allChatItems[0]) => {
    if (item.type === 'current') {
      onSelectChat(item.id);
    } else {
      onSelectHistorySession(item.id);
    }
  };

  return (
    <div style={{ 
      width: "280px", 
      backgroundColor: "#f8f9fa", 
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      borderRight: "1px solid #e1e5e9"
    }}>
      {/* Header with Model Selection */}
      <div style={{ 
        padding: "16px", 
        borderBottom: "1px solid #e1e5e9",
        backgroundColor: "white"
      }}>
        <div style={{ marginBottom: "12px" }}>
          <label htmlFor="model-select" style={{ 
            fontWeight: "600", 
            fontSize: "14px",
            color: "#374151"
          }}>
            Model:
          </label>
          <select
            id="model-select"
            value={selectedModel}
            onChange={handleModelChange}
            style={{
              marginLeft: "8px",
              padding: "4px 8px",
              borderRadius: "6px",
              border: "1px solid #d1d5db",
              fontSize: "13px",
              backgroundColor: "white"
            }}
          >
            <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
            <option value="gemini-2.5-flash-preview-04-17">Gemini 2.5 Flash Preview</option>
            <option value="gemini-2.5-pro-exp-03-25">Gemini 2.5 Pro Experimental</option>  
            <option value="deepseek-1.0">Deepseek-1.0</option>
          </select>
        </div>

        {/* New Chat Button */}
        <button 
          onClick={onNewChat}
          style={{
            width: "100%",
            padding: "10px 16px",
            backgroundColor: "#ffffff",
            border: "1px solid #d1d5db",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500",
            color: "#374151",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.2s ease"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#f3f4f6";
            e.currentTarget.style.borderColor = "#9ca3af";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#ffffff";
            e.currentTarget.style.borderColor = "#d1d5db";
          }}
        >
          <span style={{ marginRight: "8px", fontSize: "16px" }}>+</span>
          New Chat
        </button>
      </div>

      {/* Chat History */}
      <div style={{ 
        flex: 1,
        overflowY: "auto",
        padding: "8px"
      }}>
        <div style={{ 
          marginBottom: "12px", 
          padding: "8px 12px",
          fontSize: "13px",
          fontWeight: "600",
          color: "#6b7280",
          textTransform: "uppercase",
          letterSpacing: "0.05em"
        }}>
          Recent Chats
        </div>

        {allChatItems.length === 0 ? (
          <div style={{
            padding: "20px 12px",
            textAlign: "center",
            color: "#9ca3af",
            fontSize: "14px"
          }}>
            No chat history yet
          </div>
        ) : (
          allChatItems.map(item => (
            <div
              key={item.id}
              style={{
                padding: "12px",
                margin: "2px 4px",
                borderRadius: "8px",
                cursor: "pointer",
                backgroundColor: item.isActive ? "#e5f3ff" : "transparent",
                border: item.isActive ? "1px solid #bfdbfe" : "1px solid transparent",
                transition: "all 0.2s ease",
                position: "relative",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between"
              }}
              onMouseEnter={(e) => {
                if (!item.isActive) {
                  e.currentTarget.style.backgroundColor = "#f3f4f6";
                }
              }}
              onMouseLeave={(e) => {
                if (!item.isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                }
              }}
            >
              <div 
                onClick={() => handleItemClick(item)}
                style={{ flex: 1, minWidth: 0 }}
              >
                <div style={{ 
                  fontWeight: "500", 
                  fontSize: "14px",
                  color: "#1f2937",
                  marginBottom: "4px",
                  lineHeight: "1.4"
                }}>
                  {item.title}
                </div>
                <div style={{ 
                  fontSize: "12px", 
                  color: "#6b7280",
                  marginBottom: "2px"
                }}>
                  {item.subtitle}
                </div>
                <div style={{ 
                  fontSize: "11px", 
                  color: "#9ca3af"
                }}>
                  {item.date}
                </div>
              </div>

              {/* Delete button for history sessions */}
              {item.type === 'history' && onDeleteSession && (
                <button
                  onClick={(e) => handleDeleteSession(item.id, e)}
                  style={{
                    marginLeft: "8px",
                    padding: "4px 6px",
                    border: "none",
                    borderRadius: "4px",
                    backgroundColor: "transparent",
                    cursor: "pointer",
                    fontSize: "12px",
                    color: "#9ca3af",
                    transition: "all 0.2s ease"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "#fee2e2";
                    e.currentTarget.style.color = "#dc2626";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "#9ca3af";
                  }}
                  title="Delete this chat"
                >
                  ×
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Sidebar;

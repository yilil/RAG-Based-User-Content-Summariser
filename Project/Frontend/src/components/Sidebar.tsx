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
  createdAt: string;
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
  onDeleteSession,
}) => {


  // Helper function to format session title
  // Cache for original session titles to prevent title changes when session data updates
  const [sessionTitleCache, setSessionTitleCache] = React.useState<{[key: string]: string}>({});

  // Clean up title cache when history sessions change
  React.useEffect(() => {
    const currentSessionIds = new Set(historySessions.map(session => session.session_id));
    const cachedSessionIds = Object.keys(sessionTitleCache);
    
    // Remove cached titles for sessions that no longer exist
    const toRemove = cachedSessionIds.filter(id => !currentSessionIds.has(id));
    if (toRemove.length > 0) {
      setSessionTitleCache(prev => {
        const newCache = { ...prev };
        toRemove.forEach(id => delete newCache[id]);
        console.log(`Cleaned up title cache for removed sessions: ${toRemove.join(', ')}`);
        return newCache;
      });
    }
  }, [historySessions, sessionTitleCache]);

  const getSessionTitle = (session: HistorySession) => {
    // Check if we already have a cached title for this session
    if (sessionTitleCache[session.session_id]) {
      return sessionTitleCache[session.session_id];
    }

    // Generate title from the original first message
    let title: string;
    if (session.memory_data && session.memory_data.length > 0) {
      const firstMessage = session.memory_data[0].user;
      title = firstMessage.length > 35 
        ? firstMessage.substring(0, 35) + "..." 
        : firstMessage;
    } else {
      title = `${session.platform || "Unknown"} Session`;
    }

    // Cache the title so it doesn't change even if session data updates
    setSessionTitleCache(prev => ({
      ...prev,
      [session.session_id]: title
    }));

    return title;
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
        // Clean up the title cache for the deleted session
        setSessionTitleCache(prev => {
          const newCache = { ...prev };
          delete newCache[sessionId];
          console.log(`Cleaned up title cache for deleted session: ${sessionId}`);
          return newCache;
        });
      }
    }
  };

  // Helper function to check if a history session has been converted to a current chat
  const isSessionConvertedToChat = (sessionId: string) => {
    const isConverted = chats.some(chat => {
      // Check if any current chat uses this session ID as its session key
      const chatSessionKey = localStorage.getItem(`sessionKey-${chat.id}`);
      return chatSessionKey === sessionId;
    });
    
    if (isConverted) {
      console.log(`History session ${sessionId} has been converted to current chat - filtering out from sidebar`);
    }
    
    return isConverted;
  };

  // Combine current chats and history sessions for unified display
  const allChatItems = [
    // Current chats (exclude virtual chats that start with 'history-')
    ...chats
      .filter(chat => !chat.id.startsWith('history-'))
      .map(chat => ({
        id: chat.id,
        type: 'current' as const,
        title: `${chat.platform} Chat`,
        subtitle: `${chat.messages.length} messages`,
        date: formatDate(chat.createdAt),
        timestamp: chat.createdAt,
        isActive: activeChatId === chat.id
      })),
    // History sessions (exclude those that have been converted to current chats)
    ...(() => {
      const filteredSessions = historySessions.filter(session => !isSessionConvertedToChat(session.session_id));
      console.log(`=== SIDEBAR DUPLICATE FILTERING ===`);
      console.log(`Total history sessions: ${historySessions.length}`);
      console.log(`Filtered history sessions: ${filteredSessions.length}`);
      console.log(`Removed duplicates: ${historySessions.length - filteredSessions.length}`);
      console.log(`Current chats: ${chats.filter(chat => !chat.id.startsWith('history-')).length}`);
      return filteredSessions;
    })().map(session => ({
        id: session.session_id,
        type: 'history' as const,
        title: getSessionTitle(session),
        subtitle: `${session.platform || "Unknown"} • ${session.memory_data.length} messages`,
        date: formatDate(session.updated_at),
        timestamp: session.updated_at,
        // Check if this history session is currently active (either as activeHistorySessionId or as virtual chat)
        isActive: activeHistorySessionId === session.session_id || activeChatId === `history-${session.session_id}`
      }))
  ].sort((a, b) => {
    // Sort by timestamp descending (newest first)
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  const handleItemClick = (item: typeof allChatItems[0]) => {
    if (item.type === 'current') {
      onSelectChat(item.id);
    } else {
      onSelectHistorySession(item.id);
    }
  };

  return (
    <div style={{ 
      width: "240px", 
      backgroundColor: "#369496", 
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
      alignItems: "center",
      flexShrink: 0,
      borderRight: "1px solid rgba(28, 28, 28, 0.10)"
    }}>
      {/* Header with New Chat Button */}
      <div style={{ 
        height: "60px",
        padding: "8px 12px 8px 8px", 
        borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
        backgroundColor: "transparent",
        width: "240px",
        display: "flex",
        alignItems: "center",
        boxSizing: "border-box"
      }}>

        {/* New Chat Button */}
        <button 
          onClick={onNewChat}
          style={{
            display: "flex",
            padding: "8px 20px",
            justifyContent: "center",
            alignItems: "center",
            gap: "8px",
            backgroundColor: "#69C6C4",
            border: "1px solid #69C6C4",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500",
            color: "white",
            transition: "all 0.2s ease",
            margin: "2px 4px",
            width: "calc(100% - 8px)",
            boxSizing: "border-box"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#5AB3B1";
            e.currentTarget.style.borderColor = "#5AB3B1";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#69C6C4";
            e.currentTarget.style.borderColor = "#69C6C4";
          }}
        >
          <span style={{ fontSize: "16px" }}>+</span>
          New Chat
        </button>
      </div>

      {/* Chat History */}
      <div 
        className="sidebar-scroll"
        style={{ 
          flex: 1,
          overflowY: "auto",
          padding: "8px 12px 8px 8px",
          width: "100%",
          boxSizing: "border-box"
        }}
      >
        <div style={{ 
          marginBottom: "12px", 
          padding: "8px 12px",
          fontSize: "13px",
          fontWeight: "600",
          color: "rgba(255, 255, 255, 0.8)",
          textTransform: "uppercase",
          letterSpacing: "0.05em"
        }}>
          Recent Chats
        </div>

        {allChatItems.length === 0 ? (
          <div style={{
            padding: "20px 12px",
            textAlign: "center",
            color: "rgba(255, 255, 255, 0.6)",
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
                backgroundColor: item.isActive ? "rgba(255, 255, 255, 0.2)" : "transparent",
                border: item.isActive ? "1px solid rgba(255, 255, 255, 0.3)" : "1px solid transparent",
                transition: "all 0.2s ease",
                position: "relative",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between"
              }}
              onMouseEnter={(e) => {
                if (!item.isActive) {
                  e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)";
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
                  color: "white",
                  marginBottom: "4px",
                  lineHeight: "1.4"
                }}>
                  {item.title}
                </div>
                <div style={{ 
                  fontSize: "12px", 
                  color: "rgba(255, 255, 255, 0.8)",
                  marginBottom: "2px"
                }}>
                  {item.subtitle}
                </div>
                <div style={{ 
                  fontSize: "11px", 
                  color: "rgba(255, 255, 255, 0.6)"
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
                    color: "rgba(255, 255, 255, 0.6)",
                    transition: "all 0.2s ease"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
                    e.currentTarget.style.color = "#fca5a5";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "rgba(255, 255, 255, 0.6)";
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
      
      {/* Custom scrollbar styles */}
      <style>{`
        .sidebar-scroll::-webkit-scrollbar {
          width: 6px;
        }
        
        .sidebar-scroll::-webkit-scrollbar-track {
          background: rgba(105, 198, 196, 0.2);
          border-radius: 3px;
          margin: 4px 0;
        }
        
        .sidebar-scroll::-webkit-scrollbar-thumb {
          background: #69C6C4;
          border-radius: 3px;
          transition: background 0.2s ease;
        }
        
        .sidebar-scroll::-webkit-scrollbar-thumb:hover {
          background: #5AB3B1;
        }
        
        /* For Firefox */
        .sidebar-scroll {
          scrollbar-width: thin;
          scrollbar-color: #69C6C4 rgba(105, 198, 196, 0.2);
        }
      `}</style>
    </div>
  );
};

export default Sidebar;

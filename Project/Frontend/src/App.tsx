import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar"; // adjust path as needed
import PlatformSelection from "./pages/PlatformSelection"; // adjust path as needed
import SummaryPage from "./pages/SummaryPage"; // adjust path as needed

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

const BASE_URL = "http://127.0.0.1:8000";

const App: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [historySessions, setHistorySessions] = useState<HistorySession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [activeHistorySessionId, setActiveHistorySessionId] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [selectedModel, setSelectedModel] = useState("gemini-2.0-flash");
  const [showPlatformSelection, setShowPlatformSelection] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Load all history sessions on app start
  useEffect(() => {
    loadAllHistorySessions();
  }, []);

  // Load all history sessions from backend
  const loadAllHistorySessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BASE_URL}/getAllChat/`);
      if (!response.ok) {
        throw new Error(`Failed to load chat history: ${response.status}`);
      }
      const data = await response.json();
      // Filter out sessions with no memory data
      const validSessions = data.filter((session: HistorySession) => 
        session.memory_data && session.memory_data.length > 0
      );
      setHistorySessions(validSessions);
    } catch (error) {
      console.error("Failed to load history sessions:", error);
      setError("Failed to load chat history. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  // Save current session to backend
  const saveCurrentSession = async () => {
    const currentChat = chats.find(chat => chat.id === activeChatId);
    if (!currentChat || currentChat.messages.length === 0) {
      return;
    }

    try {
      // Get session key from localStorage
      const sessionKey = localStorage.getItem(`sessionKey-${currentChat.id}`);
      if (!sessionKey) {
        console.log('No session key found for current chat');
        return;
      }

      console.log('Saving current session before switch...', sessionKey);
      const response = await fetch(`${BASE_URL}/saveSession/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionKey,
          messages: currentChat.messages,
          platform: currentChat.platform,
          topic: currentChat.topic
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save session: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Current session saved successfully:', data.message);
      // Refresh history sessions to show the updated session
      await loadAllHistorySessions();
    } catch (error) {
      console.error('Error saving current session:', error);
      setError("Failed to save current session. Your progress might not be saved.");
    }
  };

  // Create a new chat when user clicks "New Chat"
  const handleNewChat = async () => {
    // Save current session before creating new one
    await saveCurrentSession();
    
    setActiveChatId(null);
    setActiveHistorySessionId(null);
    setSelectedPlatform("");
    setShowPlatformSelection(true);
  };

  // When a platform is selected, create a new chat and update state
  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowPlatformSelection(false);
    setActiveHistorySessionId(null); // Clear history session when creating new chat
    const newChatId = Math.random().toString(36).substring(2, 15);
    const newChat: Chat = {
      id: newChatId,
      platform: platform,
      topic: "",
      messages: [],
    };
    setChats(prev => [...prev, newChat]);
    setActiveChatId(newChatId);
  };

  // When a current chat is selected from the sidebar
  const handleSelectChat = async (id: string) => {
    // Save current session before switching
    await saveCurrentSession();
    
    setActiveChatId(id);
    setActiveHistorySessionId(null); // Clear history session
    setShowPlatformSelection(false);
  };

  // When a history session is selected from the sidebar
  const handleSelectHistorySession = async (sessionId: string) => {
    // Save current session before switching
    await saveCurrentSession();
    
    // Only set activeHistorySessionId, don't set activeChatId
    setActiveHistorySessionId(sessionId);
    setActiveChatId(null);
    setShowPlatformSelection(false);
  };

  // Get active chat (either current chat or virtual chat from history)
  const getActiveChat = (): Chat | null => {
    if (activeChatId) {
      return chats.find(chat => chat.id === activeChatId) || null;
    }
    
    if (activeHistorySessionId) {
      // Create virtual chat from history session
      const historySession = historySessions.find(session => session.session_id === activeHistorySessionId);
      if (historySession) {
        const messages: Message[] = [];
        historySession.memory_data.forEach((entry, index) => {
          const baseTime = new Date(historySession.updated_at);
          const userTime = new Date(baseTime.getTime() - (historySession.memory_data.length - index) * 60000);
          const botTime = new Date(baseTime.getTime() - (historySession.memory_data.length - index) * 60000 + 30000);
          
          messages.push({
            id: `${activeHistorySessionId}-user-${index}`,
            type: 'user',
            content: entry.user,
            timestamp: userTime.toISOString(),
          });
          messages.push({
            id: `${activeHistorySessionId}-bot-${index}`,
            type: 'bot',
            content: entry.ai,
            timestamp: botTime.toISOString(),
          });
        });
        
        return {
          id: activeHistorySessionId,
          platform: historySession.platform || "Unknown",
          topic: historySession.topic || "",
          messages: messages,
        };
      }
    }
    
    return null;
  };

  // Delete a history session
  const handleDeleteSession = async (sessionId: string) => {
    try {
      setLoading(true);
      console.log('Deleting session:', sessionId);
      const response = await fetch(`${BASE_URL}/deleteSession/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to delete session: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Session deleted successfully:', data.message);
      
      // If the deleted session is currently active, clear it
      if (activeHistorySessionId === sessionId) {
        setActiveHistorySessionId(null);
        setActiveChatId(null);
        setShowPlatformSelection(true);
      }
      
      // Remove the session from current chats if it's there
      setChats(prev => prev.filter(chat => chat.id !== sessionId));
      
      // Refresh history sessions
      await loadAllHistorySessions();
    } catch (error: any) {
      console.error('Error deleting session:', error);
      setError(error.message || "Failed to delete session. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Update model selection from Sidebar
  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

  // Append new message to the active chat's history
  const handleUpdateMessages = (message: Message | Message[]) => {
    // Only update messages for current chats, not history sessions
    if (!activeChatId) {
      console.log('No active chat ID, cannot update messages');
      return;
    }

    setChats(prevChats =>
      prevChats.map(chat => {
        if (chat.id === activeChatId) {
          if (Array.isArray(message)) {
            // 批量添加消息（用于历史记录加载）
            return { ...chat, messages: [...chat.messages, ...message] };
          } else {
            // 单个消息添加
            return { ...chat, messages: [...chat.messages, message] };
          }
        }
        return chat;
      })
    );
  };

  // Set messages for the active chat (replace existing messages)
  const handleSetMessages = (messages: Message[]) => {
    // Only set messages for current chats, not history sessions
    if (!activeChatId) {
      console.log('No active chat ID, cannot set messages');
      return;
    }

    setChats(prevChats =>
      prevChats.map(chat =>
        chat.id === activeChatId ? { ...chat, messages } : chat
      )
    );
  };

  const activeChat = getActiveChat();

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Error Banner */}
      {error && (
        <div style={{
          position: "fixed",
          top: "0",
          left: "0",
          right: "0",
          backgroundColor: "#fee2e2",
          borderBottom: "1px solid #fecaca",
          padding: "12px 16px",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}>
          <span style={{ color: "#dc2626", fontSize: "14px" }}>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              background: "none",
              border: "none",
              color: "#dc2626",
              cursor: "pointer",
              fontSize: "18px"
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div style={{
          position: "fixed",
          top: "0",
          left: "0",
          right: "0",
          bottom: "0",
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1001
        }}>
          <div style={{
            backgroundColor: "white",
            padding: "20px",
            borderRadius: "8px",
            textAlign: "center"
          }}>
            <div style={{ marginBottom: "10px" }}>Loading...</div>
            <div style={{
              width: "40px",
              height: "40px",
              border: "4px solid #f3f3f3",
              borderTop: "4px solid #3498db",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto"
            }}></div>
          </div>
        </div>
      )}

      <Sidebar
        chats={chats}
        historySessions={historySessions}
        activeChatId={activeChatId}
        activeHistorySessionId={activeHistorySessionId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onSelectHistorySession={handleSelectHistorySession}
        onModelChange={handleModelChange}
        onDeleteSession={handleDeleteSession}
      />

      <div style={{ flex: 1, marginTop: error ? "49px" : "0" }}>
        {showPlatformSelection && (
          <PlatformSelection onPlatformSelect={handlePlatformSelect} />
        )}

        {activeChat ? (
          <SummaryPage
            chat={activeChat}
            selectedModel={selectedModel}
            onUpdateMessages={handleUpdateMessages}
            onSetMessages={handleSetMessages}
          />
        ) : (
          !showPlatformSelection && (
            <div style={{ flex: 1, padding: "20px" }}>
              <h2>No chat selected</h2>
            </div>
          )
        )}
      </div>

      {/* CSS for loading animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default App;

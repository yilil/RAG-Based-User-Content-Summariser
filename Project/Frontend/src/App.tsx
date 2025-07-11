import React, { useState, useEffect } from "react";
import { flushSync } from "react-dom";
import Sidebar from "./components/Sidebar"; // adjust path as needed
import PlatformSelection from "./pages/PlatformSelection"; // adjust path as needed
import SummaryPage from "./pages/SummaryPage"; // adjust path as needed
import TopBar from "./components/TopBar";

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

const rawIp = import.meta.env.VITE_BASE_URL;
const BASE_URL = rawIp && rawIp.length > 0
  ? `http://${rawIp}:8000`
  : 'http://127.0.0.1:8000';

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
  
  // Cache for virtual chats to avoid recreating objects on every render
  const [virtualChatCache, setVirtualChatCache] = useState<{[key: string]: Chat}>({});

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Load all history sessions on app start
  useEffect(() => {
    loadAllHistorySessions(true); // Clear cache on initial load
  }, []);

  // Debug virtual chat cache changes
  useEffect(() => {
    console.log(`=== VIRTUAL CHAT CACHE DEBUG ===`);
    console.log('Cache keys:', Object.keys(virtualChatCache));
    console.log('Cache size:', Object.keys(virtualChatCache).length);
    if (activeHistorySessionId) {
      const cacheKey = `history-${activeHistorySessionId}`;
      console.log(`Current active session ${activeHistorySessionId} cached:`, !!virtualChatCache[cacheKey]);
    }
    console.log(`=== VIRTUAL CHAT CACHE DEBUG END ===`);
  }, [virtualChatCache, activeHistorySessionId]);

  // Load all history sessions from backend
  const loadAllHistorySessions = async (shouldClearCache: boolean = false) => {
    try {
      setLoading(true);
      console.log('Loading all history sessions...');
      const response = await fetch(`${BASE_URL}/getAllChat/`);
      if (!response.ok) {
        throw new Error(`Failed to load chat history: ${response.status}`);
      }
      const data = await response.json();
      console.log('Raw sessions data from server:', data.length);
      // Filter out sessions with no memory data
      const validSessions = data.filter((session: HistorySession) => 
        session.memory_data && session.memory_data.length > 0
      );
      console.log('Valid sessions after filtering:', validSessions.length);
      console.log('Session IDs:', validSessions.map(s => s.session_id));
      setHistorySessions(validSessions);
      
      // Only clear virtual chat cache when explicitly requested
      // This prevents unnecessary cache clearing on routine updates
      if (shouldClearCache) {
        console.log('Clearing virtual chat cache due to explicit request');
        setVirtualChatCache({});
      } else {
        console.log('Preserving virtual chat cache');
      }
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
      // Don't clear cache since we're just updating existing sessions
      await loadAllHistorySessions(false);
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
      createdAt: new Date().toISOString(),
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
    
    console.log(`=== HISTORY SESSION SELECT DEBUG ===`);
    console.log(`Selecting history session: ${sessionId}`);
    console.log(`Previous activeHistorySessionId: ${activeHistorySessionId}`);
    console.log(`Cache keys before selection:`, Object.keys(virtualChatCache));
    console.log(`Cache for session ${sessionId} exists:`, !!virtualChatCache[`history-${sessionId}`]);
    
    // Only set activeHistorySessionId, don't set activeChatId
    setActiveHistorySessionId(sessionId);
    setActiveChatId(null);
    setShowPlatformSelection(false);
    
    console.log(`=== HISTORY SESSION SELECT DEBUG END ===`);
  };

  // Get active chat (either current chat or virtual chat from history)
  const getActiveChat = (): Chat | null => {
    if (activeChatId) {
      return chats.find(chat => chat.id === activeChatId) || null;
    }
    
    if (activeHistorySessionId) {
      // Check cache first to avoid recreating the same virtual chat
      const cacheKey = `history-${activeHistorySessionId}`;
      if (virtualChatCache[cacheKey]) {
        console.log(`Using cached virtual chat for session: ${activeHistorySessionId}`);
        return virtualChatCache[cacheKey];
      }
      
      // Create virtual chat from history session
      const historySession = historySessions.find(session => session.session_id === activeHistorySessionId);
      if (historySession) {
        console.log(`Creating new virtual chat for session: ${activeHistorySessionId}`);
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
        
        const virtualChat: Chat = {
          id: `history-${activeHistorySessionId}`, // Use special prefix for virtual chats
          platform: historySession.platform || "Unknown",
          topic: historySession.topic || "",
          messages: messages,
          createdAt: historySession.updated_at, // Use session's update time as creation time
        };
        
        // Cache the virtual chat
        setVirtualChatCache(prev => ({
          ...prev,
          [cacheKey]: virtualChat
        }));
        
        return virtualChat;
      }
    }
    
    return null;
  };

  // Delete a history session
  const handleDeleteSession = async (sessionId: string) => {
    try {
      setLoading(true);
      console.log('=== DELETE SESSION DEBUG ===');
      console.log('Deleting session:', sessionId);
      console.log('Current historySessions before delete:', historySessions.length);
      console.log('Active history session ID:', activeHistorySessionId);
      
      const response = await fetch(`${BASE_URL}/deleteSession/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId
        }),
      });

      console.log('Delete response status:', response.status);
      console.log('Delete response ok:', response.ok);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Delete error response:', errorData);
        throw new Error(errorData.error || `Failed to delete session: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Session deleted successfully:', data.message);
      console.log('Delete response data:', data);
      
      // If the deleted session is currently active, clear it
      if (activeHistorySessionId === sessionId) {
        console.log('Clearing active session because it was deleted');
        setActiveHistorySessionId(null);
        setActiveChatId(null);
        setShowPlatformSelection(true);
      }
      
      // Remove the session from current chats if it's there
      // Find chats that use this sessionId as their sessionKey
      setChats(prev => {
        const chatsToRemove: string[] = [];
        const filtered = prev.filter(chat => {
          const chatSessionKey = localStorage.getItem(`sessionKey-${chat.id}`);
          if (chatSessionKey === sessionId) {
            console.log(`Found chat ${chat.id} using deleted session ${sessionId} - removing it`);
            chatsToRemove.push(chat.id);
            // Clean up localStorage entry
            localStorage.removeItem(`sessionKey-${chat.id}`);
            return false; // Remove this chat
          }
          return true; // Keep this chat
        });
        
        console.log('Chats before filter:', prev.length, 'after filter:', filtered.length);
        console.log('Removed chats using deleted session:', chatsToRemove);
        return filtered;
      });
      
      // Clear cache for the deleted session
      const cacheKey = `history-${sessionId}`;
      setVirtualChatCache(prev => {
        const newCache = { ...prev };
        delete newCache[cacheKey];
        console.log(`Removed cache for deleted session: ${cacheKey}`);
        return newCache;
      });
      
      // Refresh history sessions
      console.log('Refreshing history sessions...');
      // Clear cache since sessions have been deleted
      await loadAllHistorySessions(true);
      console.log('History sessions refreshed');
      console.log('=== DELETE SESSION DEBUG END ===');
    } catch (error: any) {
      console.error('Error deleting session:', error);
      console.error('Error stack:', error.stack);
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
    console.log('=== HANDLE UPDATE MESSAGES DEBUG ===');
    console.log('Active Chat ID:', activeChatId);
    console.log('Active History Session ID:', activeHistorySessionId);
    console.log('Message to add:', Array.isArray(message) ? `Array of ${message.length} messages` : 'Single message');
    console.log('Message content:', Array.isArray(message) ? message.map(m => m.content) : message.content);
    
    if (activeChatId) {
      // Handle regular chats
      console.log('Updating messages for regular chat:', activeChatId);
      setChats(prevChats => {
        const updatedChats = prevChats.map(chat => {
          if (chat.id === activeChatId) {
            console.log(`Found matching chat ${activeChatId}, current message count: ${chat.messages.length}`);
            if (Array.isArray(message)) {
              const newMessages = [...chat.messages, ...message];
              console.log(`Adding ${message.length} messages, new total: ${newMessages.length}`);
              return { ...chat, messages: newMessages };
            } else {
              const newMessages = [...chat.messages, message];
              console.log(`Adding 1 message, new total: ${newMessages.length}`);
              return { ...chat, messages: newMessages };
            }
          }
          return chat;
        });
        console.log('Updated chats array');
        return updatedChats;
      });
    } else if (activeHistorySessionId) {
      // Handle history sessions - convert to regular chat when user adds new message
      console.log('Converting history session to regular chat:', activeHistorySessionId);
      const historySession = historySessions.find(session => session.session_id === activeHistorySessionId);
      if (historySession) {
        // Get the current virtual chat's messages instead of recreating from memory_data
        // This avoids duplication and uses the correctly formatted messages
        const currentChat = getActiveChat();
        const existingMessages = currentChat ? currentChat.messages : [];
        
        console.log(`=== VIRTUAL CHAT MESSAGES DEBUG ===`);
        console.log(`Current virtual chat:`, currentChat);
        console.log(`Existing messages count:`, existingMessages.length);
        console.log(`Existing messages preview:`, existingMessages.slice(-3).map(m => `${m.type}: ${m.content.substring(0, 50)}`));
        console.log(`=== VIRTUAL CHAT MESSAGES DEBUG END ===`);

        // Add new messages to existing messages
        const allMessages = Array.isArray(message) 
          ? [...existingMessages, ...message]
          : [...existingMessages, message];

        console.log(`=== NEW CHAT CREATION DEBUG ===`);
        console.log(`Messages being added:`, Array.isArray(message) ? message.map(m => `${m.type}: ${m.content.substring(0, 50)}`) : `${message.type}: ${message.content.substring(0, 50)}`);
        console.log(`All messages for new chat:`, allMessages.length);
        console.log(`Last 3 messages:`, allMessages.slice(-3).map(m => `${m.type}: ${m.content.substring(0, 50)}`));

        // Create new chat with combined messages and new ID
        const newChatId = Math.random().toString(36).substring(2, 15);
        const newChat: Chat = {
          id: newChatId,
          platform: historySession.platform || "Unknown",
          topic: historySession.topic || "",
          messages: allMessages,
          createdAt: new Date().toISOString(), // Set current time as creation time when converting from history
        };
        
        console.log(`Created new chat with ${newChat.messages.length} messages`);
        console.log(`=== NEW CHAT CREATION DEBUG END ===`);

        // Do not reuse the old session key - let the new chat create its own session
        // This prevents old session content from being automatically loaded into the new chat

        // Clear the virtual chat cache for this session since it's being converted
        const cacheKey = `history-${activeHistorySessionId}`;
        setVirtualChatCache(prev => {
          const newCache = { ...prev };
          delete newCache[cacheKey];
          console.log(`Cleared cache for converted session: ${cacheKey}`);
          return newCache;
        });

        console.log(`=== HISTORY CONVERSION DEBUG ===`);
        console.log(`Converting history session ${activeHistorySessionId} to new chat ${newChatId}`);
        console.log(`Existing messages from virtual chat:`, existingMessages.length);
        console.log(`New messages being added:`, Array.isArray(message) ? message.length : 1);
        console.log(`Total messages in new chat:`, allMessages.length);
        console.log(`New chat will create its own session key`);

        // Add to chats and switch to regular chat mode using atomic state updates
        console.log(`=== ATOMIC STATE UPDATE START ===`);
        
        // First update chats array
        setChats(prevChats => {
          const newChats = [...prevChats, newChat];
          console.log(`Added new chat to chats array, total chats: ${newChats.length}`);
          console.log(`New chat in array:`, newChats.find(c => c.id === newChatId));
          return newChats;
        });
        
        // Then atomically switch to the new chat
        console.log(`Setting activeChatId to: ${newChatId}`);
        console.log(`Clearing activeHistorySessionId`);
        
        // Use flushSync to ensure synchronous updates
        flushSync(() => {
          setActiveChatId(newChatId);
          setActiveHistorySessionId(null);
        });
        
        console.log(`=== ATOMIC STATE UPDATE END ===`);
        
        console.log(`=== HISTORY CONVERSION DEBUG END ===`);
      } else {
        console.log(`ERROR: History session ${activeHistorySessionId} not found in historySessions array`);
      }
    } else {
      console.log('No active chat or history session, cannot update messages');
    }
    console.log('=== HANDLE UPDATE MESSAGES DEBUG END ===');
  };

  // Set messages for the active chat (replace existing messages)
  const handleSetMessages = (messages: Message[]) => {
    if (activeChatId) {
      // Handle regular chats
      console.log('Setting messages for regular chat:', activeChatId);
      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === activeChatId ? { ...chat, messages } : chat
        )
      );
    } else {
      // For history sessions, we don't typically replace messages
      // This function is mainly used for loading history into new chats
      console.log('SetMessages called for history session - ignoring as history is already loaded');
    }
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
        onDeleteSession={handleDeleteSession}
      />

      <div style={{ 
        flex: 1, 
        marginTop: error ? "49px" : "0",
        height: "100vh" 
      }}>
        {showPlatformSelection && (
          <PlatformSelection 
            onPlatformSelect={handlePlatformSelect}
            selectedModel={selectedModel}
            onModelChange={handleModelChange}
          />
        )}

        {activeChat ? (
          <SummaryPage
            chat={activeChat}
            selectedModel={selectedModel}
            onUpdateMessages={handleUpdateMessages}
            onSetMessages={handleSetMessages}
            onModelChange={handleModelChange}
          />
        ) : (
          !showPlatformSelection && (
            <div style={{ 
              display: "flex",
              flexDirection: "column",
              height: "100vh",
              width: "100%",
            }}>
              <TopBar 
                selectedModel={selectedModel}
                onModelChange={handleModelChange}
              />
              <div style={{ 
                height: "calc(100vh - 60px)",
                padding: "20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <h2>No chat selected</h2>
              </div>
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

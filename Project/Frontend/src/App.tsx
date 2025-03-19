import React, { useState } from "react";
import Sidebar from "./components/Sidebar"; // adjust path as needed
import PlatformSelection from "./pages/PlatformSelection"; // adjust path as needed
import SummaryPage from "./pages/SummaryPage"; // adjust path as needed

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: string[];
};

const App: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [selectedModel, setSelectedModel] = useState("gemini-1.5-flash");
  const [showPlatformSelection, setShowPlatformSelection] = useState(true);

  // Create a new chat when user clicks "New Chat"
  const handleNewChat = () => {
    setActiveChatId(null);
    setSelectedPlatform("");
    setShowPlatformSelection(true);
  };

  // When a platform is selected, create a new chat and update state
  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowPlatformSelection(false);
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

  // When a chat is selected from the sidebar
  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
  };

  // Update model selection from Sidebar
  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

  // Append new message to the active chat's history
  const handleUpdateMessages = (message: string) => {
    setChats(prevChats =>
      prevChats.map(chat =>
        chat.id === activeChatId ? { ...chat, messages: [...chat.messages, message] } : chat
      )
    );
  };

  const activeChat = chats.find(chat => chat.id === activeChatId);

  return (
    <div style={{ display: "flex" }}>
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onModelChange={handleModelChange}
      />

      {showPlatformSelection && (
        <PlatformSelection onPlatformSelect={handlePlatformSelect} />
      )}

      {activeChat ? (
        <SummaryPage
          chat={activeChat}
          selectedModel={selectedModel}
          onUpdateMessages={handleUpdateMessages}
        />
      ) : (
        !showPlatformSelection && (
          <div style={{ flex: 1, padding: "20px" }}>
            <h2>No chat selected</h2>
          </div>
        )
      )}
    </div>
  );
};

export default App;

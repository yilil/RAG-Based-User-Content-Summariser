import React, { useState } from "react";
import Sidebar from "./components/Sidebar";
import PlatformSelection from "./pages/PlatformSelection";
import TopicSelection from "./pages/TopicSelection";
import SummaryPage from "./pages/SummaryPage";

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: string[];
};

const App: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [showPlatformSelection, setShowPlatformSelection] = useState(false);
  const [showTopicSelection, setShowTopicSelection] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [selectedModel, setSelectedModel] = useState("Gemini"); // Track selected model

  // When starting a new chat, reset state appropriately.
  const handleNewChat = () => {
    setActiveChatId(null);
    setSelectedPlatform("");
    setShowTopicSelection(false);
    setShowPlatformSelection(true);
  };

  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowPlatformSelection(false);
    setShowTopicSelection(true);
  };

  const handleTopicSelect = (topic: string) => {
    const newChatId = Math.random().toString(36).substring(2, 15); // Generate random ID
    const newChat: Chat = {
      id: newChatId,
      platform: selectedPlatform,
      topic,
      messages: [],
    };
    setChats([...chats, newChat]);
    setActiveChatId(newChatId);
    setShowTopicSelection(false);
  };

  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    console.log(`Model switched to: ${model}`);
  };

  // Update messages for the active chat.
  const handleUpdateChatMessages = (message: string) => {
    if (!activeChatId) return;
    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === activeChatId
          ? { ...chat, messages: [...chat.messages, message] }
          : chat
      )
    );
  };

  const activeChat = chats.find((chat) => chat.id === activeChatId);

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

      {showTopicSelection && (
        <TopicSelection
          platform={selectedPlatform}
          onTopicSelect={handleTopicSelect}
        />
      )}

      {/* When a chat is active, pass the entire chat object along with the callback */}
      {!showPlatformSelection && !showTopicSelection && activeChat && (
        <SummaryPage
          chat={activeChat}
          selectedModel={selectedModel}
          onUpdateMessages={handleUpdateChatMessages}
        />
      )}

      {!showPlatformSelection && !showTopicSelection && !activeChat && (
        <div style={{ flex: 1, padding: "20px" }}>
          <h2>No chat selected</h2>
        </div>
      )}
    </div>
  );
};

export default App;

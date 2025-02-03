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

  const handleNewChat = () => {
    setShowPlatformSelection(true); // Show platform selection page
  };

  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform); // Save the selected platform
    setShowPlatformSelection(false);
    setShowTopicSelection(true); // Show topic selection page
  };

  const handleTopicSelect = (topic: string) => {
    const newChatId = Math.random().toString(36).substring(2, 15); // Generate random ID
    const newChat: Chat = {
      id: newChatId,
      platform: selectedPlatform,
      topic,
      messages: [],
    };
    setChats([...chats, newChat]); // Add new chat to state
    setActiveChatId(newChatId); // Set the newly created chat as active
    setShowTopicSelection(false); // Hide topic selection
  };

  const handleSelectChat = (id: string) => {
    setActiveChatId(id); // Set selected chat as active
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model); // Update the selected model
    console.log(`Model switched to: ${model}`); // Debugging log
  };

  return (
    <div style={{ display: "flex" }}>
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onModelChange={handleModelChange} // Pass model change handler
      />

      {/* Show platform selection */}
      {showPlatformSelection && (
        <PlatformSelection onPlatformSelect={handlePlatformSelect} />
      )}

      {/* Show topic selection */}
      {showTopicSelection && (
        <TopicSelection
          platform={selectedPlatform}
          onTopicSelect={handleTopicSelect}
        />
      )}

      {/* Main chat area (SummaryPage) */}
      {!showPlatformSelection && !showTopicSelection && activeChatId && (
        <SummaryPage
          platform={
            chats.find((chat) => chat.id === activeChatId)?.platform || "Unknown"
          }
          topic={
            chats.find((chat) => chat.id === activeChatId)?.topic || "Unknown"
          }
        />
      )}

      {/* Default message when no active chat */}
      {!showPlatformSelection && !showTopicSelection && !activeChatId && (
        <div style={{ flex: 1, padding: "20px" }}>
          <h2>No chat selected</h2>
        </div>
      )}
    </div>
  );
};

export default App;

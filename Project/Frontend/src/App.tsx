import React, { useState } from "react";
import Sidebar from "./components/Sidebar"; // Adjust path if needed
import PlatformSelection from "./pages/PlatformSelection"; // Adjust path if needed
import SummaryPage from "./pages/SummaryPage"; // Adjust path if needed
// import TopicSelection from "./pages/TopicSelection"; // If you removed this page

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
  // const [showTopicSelection, setShowTopicSelection] = useState(false); // If you removed the separate topic page

  // Create a new chat
  const handleNewChat = () => {
    setActiveChatId(null);
    setSelectedPlatform("");
    setShowPlatformSelection(true);
    // setShowTopicSelection(false);
  };

  // When a user picks a platform
  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowPlatformSelection(false);

    // Create a new chat with empty topic
    const newChatId = Math.random().toString(36).substring(2, 15);
    const newChat: Chat = {
      id: newChatId,
      platform: platform,
      topic: "",
      messages: [],
    };
    setChats((prev) => [...prev, newChat]);
    setActiveChatId(newChatId);
  };

  // When a user picks a chat from the sidebar
  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
  };

  // Model selection from the sidebar
  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

  // Updating the chat messages
  const handleUpdateMessages = (message: string) => {
    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === activeChatId
          ? { ...chat, messages: [...chat.messages, message] }
          : chat
      )
    );
  };

  // Find the active chat
  const activeChat = chats.find((chat) => chat.id === activeChatId);

  return (
    <div style={{ display: "flex" }}>
      {/* Sidebar with model selection and chat list */}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onModelChange={handleModelChange}
      />

      {/* Show platform selection if needed */}
      {showPlatformSelection && (
        <PlatformSelection onPlatformSelect={handlePlatformSelect} />
      )}

      {/* If you had a separate topic selection, you could conditionally render it here */}
      {/* {showTopicSelection && (
        <TopicSelection
          platform={selectedPlatform}
          onTopicSelect={handleTopicSelect}
        />
      )} */}

      {/* Show the SummaryPage if there's an active chat */}
      {activeChat && (
        <SummaryPage
          chat={activeChat}
          selectedModel={selectedModel}
          onUpdateMessages={handleUpdateMessages}
        />
      )}

      {/* If no active chat and not showing platform selection, show a default message */}
      {!activeChat && !showPlatformSelection && (
        <div style={{ flex: 1, padding: "20px" }}>
          <h2>No chat selected</h2>
        </div>
      )}
    </div>
  );
};

export default App;

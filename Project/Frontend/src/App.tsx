import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import PlatformSelection from './pages/PlatformSelection';
import TopicSelection from './pages/TopicSelection';
import SummaryPage from './pages/SummaryPage';

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
  const [showTopicSelection, setShowTopicSelection] = useState(false);

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
    const newChatId = Math.random().toString(36).substring(2, 15);
    const newChat: Chat = {
      id: newChatId,
      platform: selectedPlatform,
      topic: topic,
      messages: [],
    };
    setChats(prev => [...prev, newChat]);
    setActiveChatId(newChatId);
    setShowTopicSelection(false);
  };

  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

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
      {showTopicSelection && (
        <TopicSelection platform={selectedPlatform} onTopicSelect={handleTopicSelect} />
      )}
      {activeChat && (
        <SummaryPage
          chat={activeChat}
          selectedModel={selectedModel}
          onUpdateMessages={handleUpdateMessages}
        />
      )}
      {!activeChat && !showPlatformSelection && !showTopicSelection && (
        <div style={{ flex: 1, padding: "20px" }}>
          <h2>No chat selected</h2>
        </div>
      )}
    </div>
  );
};

export default App;

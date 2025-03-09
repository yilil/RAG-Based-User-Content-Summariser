import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import PlatformSelection from './pages/PlatformSelection';
import SummaryPage from './pages/SummaryPage';

type Chat = {
  id: string;
  platform: string;
  topic: string;   // Will now be selected directly in SummaryPage
  messages: string[];
};

const App: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [selectedModel, setSelectedModel] = useState("gemini-1.5-flash");
  const [showPlatformSelection, setShowPlatformSelection] = useState(true);

  // Remove showTopicSelection logic

  const handleNewChat = () => {
    setActiveChatId(null);
    setSelectedPlatform("");
    setShowPlatformSelection(true);
  };

  // Once user picks a platform, create a chat with empty topic
  const handlePlatformSelect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowPlatformSelection(false);

    const newChatId = Math.random().toString(36).substring(2, 15);
    const newChat: Chat = {
      id: newChatId,
      platform: platform,
      topic: "",   // empty topic
      messages: [],
    };
    setChats([...chats, newChat]);
    setActiveChatId(newChatId);
  };

  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

  // If you store user/bot messages, pass a callback to update them
  const handleUpdateMessages = (message: string) => {
    if (!activeChatId) return;
    setChats(prevChats =>
      prevChats.map(chat =>
        chat.id === activeChatId
          ? { ...chat, messages: [...chat.messages, message] }
          : chat
      )
    );
  };

  const activeChat = chats.find(chat => chat.id === activeChatId);

  return (
    <div style={{ display: 'flex' }}>
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
      {/* No more TopicSelection here */}
      {activeChat && (
        <SummaryPage
          chat={activeChat}
          selectedModel={selectedModel}
          onUpdateMessages={handleUpdateMessages}
        />
      )}
      {!activeChat && !showPlatformSelection && (
        <div style={{ flex: 1, padding: '20px' }}>
          <h2>No chat selected</h2>
        </div>
      )}
    </div>
  );
};

export default App;

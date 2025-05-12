import React, { useState } from "react";

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: string[];
};

interface SidebarProps {
  chats: Chat[];
  activeChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onModelChange: (model: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  chats,
  activeChatId,
  onNewChat,
  onSelectChat,
  onModelChange,
}) => {
  const [selectedModel, setSelectedModel] = useState("gemini-2.0-flash");

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    onModelChange(newModel);
  };

  return (
    <div style={{ width: "250px", backgroundColor: "#f0f0f0", padding: "20px" }}>
      {/* Model Selection */}
      <div style={{ marginBottom: "20px" }}>
        <label htmlFor="model-select" style={{ fontWeight: "bold" }}>
          Model:
        </label>
        <select
          id="model-select"
          value={selectedModel}
          onChange={handleModelChange}
          style={{
            marginLeft: "10px",
            padding: "5px",
            borderRadius: "5px",
            border: "1px solid #ccc",
          }}
        >
          <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
          <option value="gemini-2.5-flash-preview-04-17">Gemini 2.5 Flash Preview</option>
          <option value="gemini-2.5-pro-exp-03-25">Gemini 2.5 Pro Experimental</option>  
          <option value="deepseek-1.0">Deepseek-1.0</option>
        </select>
      </div>

      <h2>Chats</h2>
      {chats.map(chat => (
        <div
          key={chat.id}
          onClick={() => onSelectChat(chat.id)}
          style={{
            padding: "10px",
            cursor: "pointer",
            backgroundColor: activeChatId === chat.id ? "#ddd" : "transparent",
          }}
        >
          {chat.platform} Chat
        </div>
      ))}
      <button onClick={onNewChat}>+ New Chat</button>
    </div>
  );
};

export default Sidebar;

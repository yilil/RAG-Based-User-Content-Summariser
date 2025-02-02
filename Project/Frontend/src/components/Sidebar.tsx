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
  onModelChange: (model: string) => void; // Callback for model selection
}

const Sidebar: React.FC<SidebarProps> = ({
  chats,
  activeChatId,
  onNewChat,
  onSelectChat,
  onModelChange,
}) => {
  // Set default to the first model in the new list
  const [selectedModel, setSelectedModel] = useState("gemini 1.5 flash");

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel); // Update local state
    onModelChange(newModel); // Notify parent component
  };

  return (
    <div style={{ width: "250px", backgroundColor: "#f0f0f0", padding: "20px" }}>
      {/* Model Selection Dropdown */}
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
          <option value="gemini 1.5 flash">gemini 1.5 flash</option>
          <option value="gemini 1.0 pro">gemini 1.0 pro</option>
          <option value="gemini 1.5 pro">gemini 1.5 pro</option>
          <option value="gemini 2.0 flash exp">gemini 2.0 flash exp</option>
        </select>
      </div>

      <h2>Chats</h2>
      {chats.map((chat) => (
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

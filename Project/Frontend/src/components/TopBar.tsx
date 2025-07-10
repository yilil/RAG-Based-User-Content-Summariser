import React from "react";

interface TopBarProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
}

const TopBar: React.FC<TopBarProps> = ({
  selectedModel,
  onModelChange,
}) => {
  const modelOptions = [
    { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    { value: "gemini-2.5-flash-preview-04-17", label: "Gemini 2.5 Flash Preview" },
    { value: "gemini-2.5-pro-exp-03-25", label: "Gemini 2.5 Pro Experimental" },
    { value: "deepseek-1.0", label: "Deepseek-1.0" },
  ];

  return (
    <div style={{
      height: "60px",
      backgroundColor: "#ffffff",
      borderBottom: "1px solid #e5e7eb",
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-start",
      padding: "0 24px",
      boxShadow: "0 1px 3px 0 rgba(0, 0, 0, 0.1)",
    }}>
      {/* Model Selection */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <label style={{
          fontSize: "14px",
          fontWeight: "500",
          color: "#374151",
        }}>
          Model:
        </label>
        <select
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
          style={{
            padding: "8px 32px 8px 12px",
            borderRadius: "6px",
            border: "1px solid #d1d5db",
            backgroundColor: "white",
            fontSize: "14px",
            color: "#374151",
            cursor: "pointer",
            minWidth: "200px",
            appearance: "none",
            backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 5'><path fill='%23666' d='M2 0L0 2h4zm0 5L0 3h4z'/></svg>")`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 8px center",
            backgroundSize: "12px",
          }}
        >
          {modelOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>


    </div>
  );
};

export default TopBar; 
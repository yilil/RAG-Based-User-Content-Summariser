import React from "react";
import TopBar from "../components/TopBar";

interface PlatformSelectionProps {
  onPlatformSelect: (platform: string) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
}

const PlatformSelection: React.FC<PlatformSelectionProps> = ({ 
  onPlatformSelect, 
  selectedModel, 
  onModelChange 
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100%",
      }}
    >
      <TopBar 
        selectedModel={selectedModel}
        onModelChange={onModelChange}
      />
      
      <div
        style={{
          height: "calc(100vh - 60px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          flex: 1,
        }}
      >
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transform: "translateY(-30px)",
        }}>
          <h1 style={{
            color: "var(--Colours-Grey-11, #25272C)",
            fontSize: "32px",
            fontStyle: "normal",
            fontWeight: 700,
            lineHeight: "normal",
            marginBottom: "32px",
          }}>Choose a Platform to search</h1>
          <div style={{ display: "flex", gap: "20px" }}>
        <button
          onClick={() => onPlatformSelect("Stack Overflow")}
          style={{
            display: "flex",
            width: "280px",
            height: "120px",
            padding: "20px",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "16px",
            flexShrink: 0,
            borderRadius: "10px",
            backgroundColor: "#AAAAFF",
            border: "none",
            cursor: "pointer",
            color: "#FFFFFF",
            fontSize: "20px",
            fontStyle: "normal",
            fontWeight: 600,
            lineHeight: "normal",
          }}
        >
          Stack Overflow
        </button>
        <button
          onClick={() => onPlatformSelect("Reddit")}
          style={{
            display: "flex",
            width: "280px",
            height: "120px",
            padding: "20px",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "16px",
            flexShrink: 0,
            borderRadius: "10px",
            backgroundColor: "#69C6C4",
            border: "none",
            cursor: "pointer",
            color: "#FFFFFF",
            fontSize: "20px",
            fontStyle: "normal",
            fontWeight: 600,
            lineHeight: "normal",
          }}
        >
          Reddit
        </button>
        <button
          onClick={() => onPlatformSelect("Rednote")}
          style={{
            display: "flex",
            width: "280px",
            height: "120px",
            padding: "20px",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "16px",
            flexShrink: 0,
            borderRadius: "10px",
            backgroundColor: "#EDA0CE",
            border: "none",
            cursor: "pointer",
            color: "#FFFFFF",
            fontSize: "20px",
            fontStyle: "normal",
            fontWeight: 600,
            lineHeight: "normal",
          }}
        >
          Rednote
        </button>
        </div>
        </div>
      </div>
    </div>
  );
};

export default PlatformSelection;

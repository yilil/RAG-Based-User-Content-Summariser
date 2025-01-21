import React from "react";

interface PlatformSelectionProps {
  onPlatformSelect: (platform: string) => void; // Callback to handle platform selection
}

const PlatformSelection: React.FC<PlatformSelectionProps> = ({
  onPlatformSelect,
}) => {
  return (
    <div
      style={{
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        flex: 1,
      }}
    >
      <h1>Choose a Platform to Search</h1>
      <div style={{ display: "flex", gap: "20px", marginTop: "20px" }}>
        {/* Platform buttons */}
        <button
          className="btn purple"
          onClick={() => onPlatformSelect("Stack Overflow")}
          style={{
            backgroundColor: "#d4c2ff",
            padding: "15px 30px",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Stack Overflow
        </button>
        <button
          className="btn teal"
          onClick={() => onPlatformSelect("Reddit")}
          style={{
            backgroundColor: "#99e2db",
            padding: "15px 30px",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Reddit
        </button>
        <button
          className="btn pink"
          onClick={() => onPlatformSelect("Red Note")}
          style={{
            backgroundColor: "#f3badc",
            padding: "15px 30px",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Red Note
        </button>
      </div>
    </div>
  );
};

export default PlatformSelection;

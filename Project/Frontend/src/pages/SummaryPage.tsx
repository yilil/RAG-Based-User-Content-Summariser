import React, { useState } from "react";

interface SummaryPageProps {
  platform: string;
  topic: string;
}

const SummaryPage: React.FC<SummaryPageProps> = ({ platform, topic }) => {
  const [searchText, setSearchText] = useState("");

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value); // Update the search text state
  };

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
      <h2>
        Summary for {platform} - {topic}
      </h2>

      {/* Search Bar */}
      <div style={{ margin: "20px 0" }}>
        <input
          type="text"
          placeholder="Search in summary..."
          value={searchText}
          onChange={handleSearchChange}
          style={{
            width: "300px",
            padding: "10px",
            borderRadius: "5px",
            border: "1px solid #ccc",
          }}
        />
      </div>

      {/* Display Search Input (For Debugging/Testing) */}
      <p>Searching for: {searchText}</p>

      {/* Example Summary Content */}
      <div
        style={{
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          width: "80%",
          textAlign: "left",
          backgroundColor: "#f9f9f9",
        }}
      >
        <h3>Summary:</h3>
        <ul>
          <li>INFO1110 - Easy to learn</li>
          <li>COMP2123 - Intermediate, algorithms focused</li>
          <li>INFO1113 - Hands-on, practical projects</li>
          <li>COMP2017 - Systems programming</li>
          <li>SOFT2201 - Object-oriented design</li>
        </ul>
      </div>
    </div>
  );
};

export default SummaryPage;

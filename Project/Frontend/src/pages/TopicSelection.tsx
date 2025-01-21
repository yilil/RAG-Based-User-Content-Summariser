import React from "react";

interface TopicSelectionProps {
  platform: string; // Platform selected
  onTopicSelect: (topic: string) => void; // Callback to handle topic selection
}

const TopicSelection: React.FC<TopicSelectionProps> = ({
  platform,
  onTopicSelect,
}) => {
  // Topics for each platform
  const topics: { [key: string]: string[] } = {
    "Stack Overflow": ["JavaScript", "React", "CSS", "TypeScript"],
    Reddit: ["Academic", "Community", "Career"],
    "Red Note": ["Travel", "Food", "Fashion"],
  };

  // Check if platform exists in topics
  const topicList = topics[platform];

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
      <h2>Select a Topic on {platform}</h2>
      <div style={{ display: "flex", gap: "20px", marginTop: "20px" }}>
        {/* If platform exists in topics, display its topics */}
        {topicList ? (
          topicList.map((topic) => (
            <button
              key={topic}
              onClick={() => onTopicSelect(topic)}
              style={{
                backgroundColor: "#e4e4e4",
                padding: "15px 30px",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
              }}
            >
              {topic}
            </button>
          ))
        ) : (
          // Fallback if platform is invalid
          <p>No topics available for this platform.</p>
        )}
      </div>
    </div>
  );
};

export default TopicSelection;

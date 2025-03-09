import React, { useState, useRef } from "react";
import QuestionTemplates from "../components/QuestionTemplates"; // adjust path as needed

type Chat = {
  id: string;
  platform: string;
  topic: string;
  messages: string[];
};

interface SummaryPageProps {
  chat: Chat;
  selectedModel: string;
  onUpdateMessages: (message: string) => void;
}

const SummaryPage: React.FC<SummaryPageProps> = ({ chat, selectedModel, onUpdateMessages }) => {
  const [searchText, setSearchText] = useState("");
  const [result, setResult] = useState("");
  const [metadata, setMetadata] = useState<any>(null);
  const [llmModel, setLlmModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
  };

  const handleSearchSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    console.log("handleSearchSubmit triggered");
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Save user query in chat history
    onUpdateMessages(`User: ${searchText}`);
    console.log("Fetch response:", searchText);

    try {
      // Force values for testing:
      const normalizedSource = "rednote";
      const modelToSend = "gemini-1.5-flash";
      // Use the model and source coming from the web
      // Normalize source by converting to lower case and removing spaces
      // const normalizedSource = chat.platform.toLowerCase().replace(/\s/g, "");
      // const modelToSend = selectedModel;
      
      const response = await fetch("http://127.0.0.1:8000/search/", {
        method: "POST",
        mode: "cors",
        headers: {
          "Content-Type": "application/json",
        },
  
        body: JSON.stringify({
          search_query: searchText,
          llm_model: modelToSend,
          source: normalizedSource,
        }),
      });
      console.log("Fetch response:", searchText);


      if (!response.ok) {
        throw new Error(`Network response was not ok, status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Parsed data:", data);

      // Update state with the received data
      setResult(data.result);
      setMetadata(data.metadata);
      setLlmModel(data.llm_model);

      // Save bot response in chat history
      onUpdateMessages(`Bot: ${data.result}`);
      console.log("Received data:", data);
    } catch (err: any) {
      console.error("Error fetching search result:", err);
      setError("Failed to fetch result");
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = (template: string) => {
    const match = template.match(/_+/);
    let caretPosition = 0;
    if (match && match.index !== undefined) {
      caretPosition = match.index;
    }
    const cleanedTemplate = template.replace(/_+/, "");
    setSearchText(cleanedTemplate);
    setShowTemplates(false);
    
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.setSelectionRange(caretPosition, caretPosition);
      }
    }, 0);
  };

  return (
    <div style={{ padding: "20px", flex: 1, position: "relative" }}>
      <h2>
        Summary for {chat.platform} - {chat.topic}
      </h2>
      
      {/* Chat History */}
      <div
        style={{
          marginBottom: "20px",
          border: "1px solid #ddd",
          padding: "10px",
          borderRadius: "8px",
          maxHeight: "200px",
          overflowY: "auto",
        }}
      >
        <h3>Chat History:</h3>
        {chat.messages.map((msg, index) => (
          <p key={index} style={{ margin: "5px 0" }}>{msg}</p>
        ))}
      </div>

      {/* Search Bar Form */}
      <form onSubmit={handleSearchSubmit} style={{ margin: "20px 0", position: "relative" }}>
        <input
          ref={inputRef}
          type="text"
          placeholder="Enter your question..."
          value={searchText}
          onChange={handleSearchChange}
          onFocus={() => setShowTemplates(true)}
          onBlur={() => setTimeout(() => setShowTemplates(false), 150)}
          style={{
            width: "300px",
            padding: "10px",
            borderRadius: "5px",
            border: "1px solid #ccc",
          }}
        />
        <button
          type="submit"
          style={{
            marginLeft: "10px",
            padding: "10px 20px",
            borderRadius: "5px",
            border: "none",
            backgroundColor: "#188a8d",
            color: "white",
            cursor: "pointer",
          }}
        >
          Search
        </button>
        {showTemplates && (
          <QuestionTemplates
            platform={chat.platform}
            topic={chat.topic}
            onTemplateSelect={handleTemplateSelect}
          />
        )}
      </form>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Display Response */}
      {result && (
        <div
          style={{
            padding: "20px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            textAlign: "left",
            backgroundColor: "#f9f9f9",
          }}
        >
          <h3>Result:</h3>
          <p>{result}</p>
          <h4>Model:</h4>
          <p>{llmModel}</p>
          <h4>Metadata:</h4>
          <pre style={{ background: "#eee", padding: "10px" }}>
            {JSON.stringify(metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default SummaryPage;

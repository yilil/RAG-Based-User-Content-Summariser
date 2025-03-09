import React from "react";

interface QuestionTemplatesProps {
  platform: string;
  topic: string;
  onTemplateSelect: (template: string) => void;
}

const templates: { [platform: string]: { [topic: string]: string[] } } = {
  "Stack Overflow": {
    JavaScript: [
      "How do I fix this JavaScript error: ____?",
      "What is the best practice for async functions in JavaScript?",
      "How can I optimize my JavaScript code for performance?",
    ],
    React: [
      "How do I manage state in React when ____?",
      "What's the best way to handle component lifecycle in React?",
      "How do I optimize rendering performance in React?",
    ],
    CSS: [
      "How can I center a div using CSS in ____ layout?",
      "What are the best practices for responsive design using CSS?",
      "How do I use Flexbox to align items ____?",
    ],
    TypeScript: [
      "How do I define interfaces in TypeScript for ____?",
      "What's the best way to handle type safety when ____?",
      "How do I configure my project for TypeScript with ____?",
    ],
  },
  Reddit: {
    Academic: [
      "What are the best study tips for ____?",
      "How can I improve my research skills in ____?",
      "What resources do you recommend for understanding ____?",
    ],
    Community: [
      "How can I get more involved in my local community if ____?",
      "What are the benefits of joining community groups focused on ____?",
      "How do I start a community project about ____?",
    ],
    Career: [
      "What are the key skills needed for a career in ____?",
      "How can I transition my career from ____ to ____?",
      "What advice do you have for someone looking to start a career in ____?",
    ],
  },
  "Red Note": {
    Travel: [
      "What are the must-see destinations in ____?",
      "What travel tips do you have for visiting ____?",
      "How do I plan a budget-friendly trip to ____?",
    ],
    Food: [
      "What are the best restaurants in ____?",
      "Which local dishes should I try in ____?",
      "Where can I find authentic ____ cuisine in ____?",
    ],
    Fashion: [
      "What are the latest trends in ____ fashion?",
      "How can I style ____ for a casual look?",
      "Where can I shop for sustainable fashion in ____?",
    ],
  },
};

const QuestionTemplates: React.FC<QuestionTemplatesProps> = ({
  platform,
  topic,
  onTemplateSelect,
}) => {
  const topicTemplates = templates[platform]?.[topic] || [];

  return (
    <div
      style={{
        position: "absolute",
        backgroundColor: "#fff",
        border: "1px solid #ccc",
        borderRadius: "5px",
        width: "300px",
        marginTop: "5px",
        zIndex: 1000,
        boxShadow: "0px 4px 8px rgba(0,0,0,0.1)",
      }}
    >
      {topicTemplates.length > 0 ? (
        <ul style={{ listStyle: "none", margin: 0, padding: "10px" }}>
          {topicTemplates.map((template, index) => (
            <li
              key={index}
              onMouseDown={() => onTemplateSelect(template)}
              style={{
                padding: "8px",
                cursor: "pointer",
                borderBottom:
                  index !== topicTemplates.length - 1 ? "1px solid #eee" : "none",
              }}
            >
              {template}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ padding: "10px" }}>
          No templates available for this selection.
        </p>
      )}
    </div>
  );
};

export default QuestionTemplates;

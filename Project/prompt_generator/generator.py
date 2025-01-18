def generate_prompt(query, retrieved_docs, recent_memory):
    #提取记忆转化为string
    memory_texts = []
    if recent_memory:
        memory_texts.append("Here is the recent conversation history:\n")
        for idx, turn in enumerate(recent_memory, start=1):
            memory_texts.append(f"Turn {idx}:\nUser: {turn['user']}\nAI: {turn['ai']}\n")
        memory_texts.append("\n")
    recent_memory_str = "".join(memory_texts)


    doc_texts = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        source = doc.metadata.get("source", "unknown")
        doc_id = doc.metadata.get("id", f"?{idx}")
        snippet = f"[Doc{idx} | source={source}, id={doc_id}]\n{doc.page_content}\n\n"
        doc_texts.append(snippet)
    
    combined_docs_str = "".join(doc_texts)

    if retrieved_docs:
        prompt = (
            f"**User Query**: {query}\n\n"
            f"{recent_memory_str}"
            f"Below are the relevant documents retrieved via RAG:\n{combined_docs_str}"
            "Please review these documents and provide a concise answer to the user.\n"
            "If the provided documents do not contain sufficient information, please indicate that.\n"
        )
    else:
        prompt = (
            f"**User Query**: {query}\n\n"
            f"{recent_memory_str}"
            "No relevant documents were retrieved. Please attempt to answer based on your general knowledge.\n"
            "Every time you try to change a line, use a new line to separate the previous line.\n"
        )
    
    return prompt
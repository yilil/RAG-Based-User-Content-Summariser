def generate_prompt(query, retrieved_docs):
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
            f"Below are the relevant documents retrieved via RAG:\n{combined_docs_str}"
            "Please review these documents and provide a concise answer to the user.\n"
            "If the provided documents do not contain sufficient information, please indicate that.\n"
        )
    else:
        prompt = (
            f"**User Query**: {query}\n"
            "No relevant documents were retrieved. Please attempt to answer based on your general knowledge.\n"
        )
    
    return prompt
def generate_prompt(query, retrieved_docs, recent_memory, platform, classification):
    prompt = []

    if platform == "reddit":
        prompt.append(
            "## Role \n"+
            "You are a Reddit community information expert, able to provide comprehensive and culturally appropriate answers by analyzing Reddit's historical discussions and combining the collective wisdom of different subreddits."+
            "Your answer must be based on the content of the Reddit post provided.\n"
        )
    elif platform == "stackoverfstackoverflowlow":
        prompt.append(
            "## Role \n"+
            "You are an experienced technical consultant, and your task is to provide professional, accurate, and detailed answers based on programming questions posed by users, combined with relevant information retrieved from Stack Overflow.\n"
        )
    elif platform == "rednote":
        prompt.append(
            "## Role \n"+
            "You are an intelligent assistant, and your task is to provide accurate and helpful answers based on the user's questions and relevant post information obtained from the Little Red Book.\n"
        )


    prompt.append(f"\n## User Query:\n{query}\n\n")

    #提取记忆转化为string
    memory_texts = []
    if recent_memory:
        for idx, turn in enumerate(recent_memory, start=1):
            memory_texts.append(f"Turn {idx}:\nUser: {turn['user']}\nAI: {turn['ai']}\n")
        memory_texts.append("\n")
    recent_memory_str = "".join(memory_texts)
    prompt.append("## Chat History\n"+ f"Below are the current 5 chat history with user:\n{recent_memory_str}\n")

    doc_texts = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        source = doc.metadata.get("source", "unknown")
        doc_id = doc.metadata.get("id", f"?{idx}")
        snippet = f"[Doc{idx} | source={source}, id={doc_id}]\n{doc.page_content}\n\n"
        doc_texts.append(snippet)
    
    combined_docs_str = "".join(doc_texts)

    if retrieved_docs:
        prompt.append(
            "## Relevant Documents\n"+
            f"Below are the relevant documents retrieved via RAG, use it if you need:\n{combined_docs_str}"+
            "Please review these documents and provide a concise answer to the user if the documents have useful information.\n"+
            "If the provided documents do not contain sufficient information, please indicate that.\n\n"
        )
    else:
        prompt.append (
            "No relevant documents were retrieved. Please attempt to answer based on your general knowledge.\n\n"
        )
    
    prompt.append(
            "## Output Format  \n" +
            "If the current question is determined to be one with a definite answer, such as 23 + 1 = 24," +
            "then the first sentence should directly answer the question before providing detailed explanations.\n"+
            "The reply should be well-formed. Use MarkDown syntax to visually enhance the reply, "+
            "such as the precise sentences of the answer or the boldness of each subheading, or the emphasis on important content.\n"
    )
    result = "".join(prompt)
    print(result)
    return result

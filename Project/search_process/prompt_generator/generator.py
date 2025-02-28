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
            "The reply should be well-formed. Use MarkDown syntax to visually enhance the reply,"+
            "such as the precise sentences of the answer or the boldness of each subheading, or the emphasis on important content.\n"
    )

    print(classification)
    match classification:
        case '1':
            prompt.append("""Please recommend [specific objects, such as books/movies/tools, etc.] based on the following requirements:

Structured points: Each recommendation should contain the name, suitable audience, core advantages, potential disadvantages;

Comparison summary: The final table is used to compare the scores (1-5 points) and recommendation priorities of the recommended items;

Language style: concise and practical, avoiding subjective exaggeration, marking data sources or user evaluation basis.
Additional conditions: [e.g. budget/usage scenarios/special needs, etc.]""")
        case '2':
            prompt.append("""Please explain [professional concept/phenomenon principle] in an understandable manner, requiring:

Logical framework: Definition → Background/origin → core mechanism → real-world application examples;

Help understanding: Use metaphors/analogies to explain complex parts and mark the original English text of key terms;

Format specification: Each paragraph does not exceed 3 lines, important conclusions are bolded, and flowcharts/schematic illustrations are provided if necessary.
Supplementary note: [If you need simplified/In-depth Academic edition]""")
        case '3':
            prompt.append("""Please analyze and discuss [controversial topic], asking:

Dialectical structure: first list the supporting arguments (including data/cases), and then list the opposing arguments;

Neutral summary: Use the "comprehensive view" part to point out the consensus area and unsolved disputes, and label the information sources of all parties;

Risk Alert: Where ethical/legal issues are involved, a separate statement of potential implications is required.
Supplementary requirements: [e.g. focus on an area/exclude invalid arguments]""")
        case '4':
            prompt.append("""Please provide a complete operating guide for [specific tasks], requiring:

Step disassembly: according to the "preparation stage → core steps → acceptance criteria" step-by-step explanation, complex steps gamete steps;

Tips for avoiding pitfalls: Use ⚠️ to mark common errors and solutions, and indicate free/paid when recommending tools;

Visual aid: Key operations with ASCII schematics or symbolized flow charts.
Additional conditions: [e.g. for beginners/specific equipment/emergency]""")
        case '5':
            prompt.append("""Please provide a solution for the following scenario: [Describe scenario in detail], requiring:

Scenario modeling: First analyze the core contradictions and constraints (time/resources/capabilities, etc.);

Grading strategy: give phased suggestions according to "short-term emergency → medium-term optimization → long-term prevention";

Risk assessment: Use tables to compare the feasibility/cost/potential side effects of different options.
Additional information: [failed method if tried]""")
        case '6':
            prompt.append("""Please summarize the latest [events/areas] and request:

Information filtering: In order of importance, each dynamic contains time/place/subject/scope of influence;

Credibility marks: ✅ for official information, ❓ for unconfirmed information, and hyperlinks to cited sources (if available);

Trend prediction: Use the "expert opinion" section to explain the likely direction of development, separating fact from speculation.
Time frame: [e.g. near 24 hours/this week/this month]""")
        case _:
            prompt.append("""If the current question is determined to be one with a definite answer, such as 23 + 1 = 24," +
            "then the first sentence should directly answer the question before providing detailed explanations.\n""")

    result = "".join(prompt)
    return result

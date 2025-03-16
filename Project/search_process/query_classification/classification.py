from search_process.prompt_sender.sender import send_prompt_to_gemini, send_prompt_to_deepseek, send_prompt_to_chatgpt
from search_process.langchain_parser.parser import parse_langchain_response

def classify_query(query, model_name):
    prompt = []
    prompt.append(f"## User Query:\n{query}\n\n")
    prompt.append("You need to judge the user's query and categorize the question with following categories, not answer the question but categorize it.\n")
    prompt.append("""1. Recommendation class, e.g.: What are some good books to learn Python for beginners?
2. Knowledge interpretation) class, e.g.: How does blockchain technology work?
3. Opinion Discussion, e.g.: Should social media platforms regulate free speech?
4. Operation instruction and tutorial method class, e.g.: How do I reset my iPhone to factory settings?
5. Specific scenarios(The user gives a long description of his situation and then asks the question of what to do next), e.g.: I've been running a small online store for six months. I get decent traffic, but sales conversions are low. I've optimized my website speed, improved product descriptions, and offered discounts, but it hasn't helped much. What should I do next?
6. Information and real-time dynamic class, e.g.: What are the latest updates on the AI Act regulations in the European Union?\n""")
    prompt.append("Just answer the order of the category, for example, if the user's query is a recommendation class, you should answer 1\n")
    prompt.append("Your answer should be a number from 1 to 6 and no other content is needed, don't include markdown syntax etc.\n") 
    prompt = "".join(prompt)

    if model_name.startswith("gemini"):
        response = send_prompt_to_gemini(prompt, model_name)
    elif model_name.startswith("deepseek"):
        response = send_prompt_to_deepseek(prompt, model_name)
    elif model_name.startswith("gpt"):
        response = send_prompt_to_chatgpt(prompt, model_name)
    else:
        return f"Error: Unsupported model name {model_name}"
    
    print(response)
    answer, metadata = parse_langchain_response(response)
    return answer
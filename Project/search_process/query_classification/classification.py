from search_process.prompt_sender.sender import send_prompt_to_gemini, send_prompt_to_deepseek, send_prompt_to_chatgpt
from search_process.langchain_parser.parser import parse_langchain_response

def classify_query(query, model_name):
    prompt = []
    prompt.append(f"## User Query:\n{query}\n\n")
    prompt.append("You need to judge the user's query and categorize the question with following categories, not answer the question but categorize it.\n")
    prompt.append("""1. Recommendation class
2. Knowledge interpretation) class
3. Opinion Discussion
4. Operation instruction and tutorial method class
5. Specific scenarios
6. Information and real-time dynamic class""")
    prompt.append("Just answer the order of the category, for example, if the user's query is a recommendation class, you should answer 1")
    prompt.append("Your answer should be a number from 1 to 6 and no other content is needed, don't include markdown syntax etc.") 
    prompt = "".join(prompt)

    if model_name.startswith("gemini"):
        response = send_prompt_to_gemini(prompt, model_name)
    elif model_name.startswith("deepseek"):
        response = send_prompt_to_deepseek(prompt, model_name)
    elif model_name.startswith("gpt"):
        response = send_prompt_to_chatgpt(prompt, model_name)
    else:
        return f"Error: Unsupported model name {model_name}"
    
    answer, metadata = parse_langchain_response(response)
    return answer
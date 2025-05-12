import time
import google.generativeai as genai
import os
import requests
import openai

def send_prompt_to_gemini(prompt, model_name="gemini-2.0-flash"):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("No API key found!")
        return "Error: GEMINI_API_KEY not found in environment variables"
    
    print(f"Found API key: {key[:5]}...") 
    
    try:
        print("Configuring genai...")
        genai.configure(api_key=key)
        
        print(f"Creating model instance for {model_name}...")
        model = genai.GenerativeModel(model_name)

        print(f"Sending query to Gemini API: {prompt}")
        start_time = time.time()
        
        response = model.generate_content(prompt)
        
        print(f"Response received in {time.time() - start_time:.2f} seconds")
        print(f"Full response: {response}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

def send_prompt_to_deepseek(prompt, model_name="deepseek-1.0"):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("No API key found!")
        return "Error: DEEPSEEK_API_KEY not found in environment variables"
    
    try:
        client = openai.OpenAI(api_key=key, base_url="https://api.deepseek.com")

        print(f"Sending query to DeepSeek API: {prompt}")
        start_time = time.time()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        print(f"Response received in {time.time() - start_time:.2f} seconds")
        print(f"Full response: {response}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

def send_prompt_to_chatgpt(prompt, model_name="gpt-3.5-turbo"):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("No API key found!")
        return "Error: OPENAI_API_KEY not found in environment variables"
    
    try:
        openai.api_key = key

        print(f"Sending query to ChatGPT API: {prompt}")
        start_time = time.time()
        response = openai.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        print(f"Response received in {time.time() - start_time:.2f} seconds")
        print(f"Full response: {response}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

def send_prompt(prompt, model_name):
    if model_name.startswith("gemini"):
        return send_prompt_to_gemini(prompt, model_name)
    elif model_name.startswith("deepseek"):
        return send_prompt_to_deepseek(prompt, model_name)
    elif model_name.startswith("gpt"):
        return send_prompt_to_chatgpt(prompt, model_name)
    else:
        return f"Error: Unsupported model name {model_name}"
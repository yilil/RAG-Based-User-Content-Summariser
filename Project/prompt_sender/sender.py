import time
import google.generativeai as genai
import os

def send_prompt_to_gemini(prompt, model_name="gemini-1.5-flash"):
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
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error processing query: {str(e)}"
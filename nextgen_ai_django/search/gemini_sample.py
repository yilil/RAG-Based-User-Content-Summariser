import time
import google.generativeai as genai
import os

def process_search_query(query):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("No API key found!")
        return "Error: GEMINI_API_KEY not found in environment variables"
    
    print(f"Found API key: {key[:5]}...") 
    
    try:
        print("Configuring genai...")
        genai.configure(api_key=key)
        
        print("Creating model instance...")
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        print(f"Sending query to Gemini API: {query}")
        start_time = time.time()
        
        response = model.generate_content(query)
        
        print(f"Response received in {time.time() - start_time:.2f} seconds")
        print(f"Full response: {response}")
        print(f"Response text: {response.text}")
        return response.text
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error processing query: {str(e)}"
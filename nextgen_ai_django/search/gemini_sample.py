import google.generativeai as genai




def process_search_query(query):
    file_path = 'search/gemini.zshrc'
    key = ''
    try:
        with open(file_path, "r") as file:
            key = file.read()
    except FileNotFoundError:
        print(f"Cannot find {file_path}")
        return ''
    except Exception as e:
        print(f"Error when reading config: {e}")
        return ''

    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(query)
    return response.text
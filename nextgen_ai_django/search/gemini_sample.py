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

# # Process the search query and return relevant results
# def process_search_query(query, documents):
#     """
#     Processes the search query and filters the relevant results.

#     :param query: The search query input from the user
#     :param documents: A list of documents fetched from the database
#     :return: A list of documents that match the query
#     """
#     relevant_docs = []  # List to store relevant documents
#     for doc in documents:
#         # Check if the search query is in the content (case-insensitive)
#         if query.lower() in doc["content"].lower():
#             relevant_docs.append(doc)

#     return relevant_docs  # Return the filtered list
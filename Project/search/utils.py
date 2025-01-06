from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
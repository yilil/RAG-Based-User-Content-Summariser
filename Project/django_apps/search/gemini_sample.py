import time
import google.generativeai as genai
import os
import sys
def process_search_query(query, retrieved_docs = None):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("No API key found!")
        return "Error: GEMINI_API_KEY not found in environment variables"
    
    print(f"Found API key: {key[:5]}...") 
    
    try:
        print("Configuring genai...")
        genai.configure(api_key=key)
        
        print("Creating model instance...")
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
        #gemini-2.0-flash

        """
        Combine the retrieved documents with the prompt template
        """
        if retrieved_docs and len(retrieved_docs) > 0:
            # 'retrieved_docs' is a list of Document objects returned by FAISS similarity_search()
            doc_texts = []
            for idx, doc in enumerate(retrieved_docs, start=1):
                source = doc.metadata.get("source", "unknown")
                doc_id = doc.metadata.get("id", f"?{idx}")
                snippet = f"[Doc{idx} | source={source}, id={doc_id}]\n{doc.page_content}\n\n"
                doc_texts.append(snippet)
            
            combined_docs_str = "".join(doc_texts)

            # RAG-based prompt
            prompt = (
                f"**User Query**: {query}\n\n"
                f"Below are the relevant documents retrieved via RAG:\n{combined_docs_str}"
                "Please review these documents and provide a concise answer to the user.\n"
                "If the provided documents do not contain sufficient information, please indicate that.\n"
            )
        # TO BE DONE: If no retrieved documents found, we need to adjust to another method
        else: 
            prompt = (
                f"**User Query**: {query}\n"
                "No relevant documents were retrieved. Please attempt to answer based on your general knowledge.\n"
            )
        
        
        print(f"Sending query to Gemini API: {query}")
        start_time = time.time()
        
        response = model.generate_content(prompt)
        
        print(f"Response received in {time.time() - start_time:.2f} seconds")
        print(f"Full response: {response}")
        print(f"Response text: {response.text}")
        return response.text
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error processing query: {str(e)}"


def main():
    print("=== Gemini Query Processor ===")
    print("输入 'exit' 可退出程序。\n")

    while True:
        user_input = input("请输入查询内容: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("已退出。")
            break

        # retrieved_docs 示例，实际使用时应来自向量数据库（如 FAISS）
        # 这里只是模拟，没有向量搜索逻辑
        fake_retrieved_docs = None  # 或者构造一个假数据列表以测试带文档的逻辑

        result = process_search_query(user_input, retrieved_docs=fake_retrieved_docs)
        print("\n=== 回答结果 ===")
        print(result)
        print("=" * 40 + "\n")


if __name__ == "__main__":
    main()

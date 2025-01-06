import logging
import concurrent
from django.shortcuts import render
from django.http import HttpResponse
from .index_service import IndexService

import search.gemini_sample as gs

# Initialize logger
logger = logging.getLogger(__name__)

def search(request):
    print("Request method:", request.method)  
    print("POST data:", request.POST)       
    result = None

    if request.method == "POST":
        search_query = request.POST.get('search_query')
        if search_query:  
            print(f"Received search query: {search_query}")
            
            # 先调用IndexService的FAISS搜索
            try:
                index_service = IndexService()
                # 这里假设已经建好了faiss_index并可直接load
                retrieved_docs = index_service.faiss_search(
                    query=search_query, 
                    top_k=5
                )
            except Exception as e:
                print(f"Error during FAISS search: {str(e)}")
                retrieved_docs = []

            # 并发调用 Gemini
            # 将 retrieved_docs 一并传入 process_search_query
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(gs.process_search_query, search_query, retrieved_docs)
                    try:
                        result = future.result(timeout=30)
                    except concurrent.futures.TimeoutError:
                        print("Query timed out after 30 seconds")
                        result = "Error: Request timed out. Please try again."
                    
            except Exception as e:
                print(f"Error in view concurrency block: {str(e)}")
                result = f"Error: {str(e)}"

    return render(request, 'searchwithTemple.html', {'result': result})


# Initialization of indexing and embeddings
def index_content(request):
    index_service = IndexService()

    try:
        # 先向ContentIndex表插入embedding
        index_service.index_reddit_content()
        index_service.index_stackoverflow_content()
        # 然后构建并保存FAISS索引
        index_service.build_faiss_index()

        return HttpResponse("Indexing finished.")
    
    except Exception as e:
        logger.error(f"Error during indexing: {str(e)}")
        return HttpResponse(f"Error during indexing: {str(e)}", status=500)
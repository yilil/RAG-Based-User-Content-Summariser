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
            
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(gs.process_search_query, search_query)
                    try:
                        result = future.result(timeout=30)
                    except concurrent.futures.TimeoutError:
                        print("Query timed out after 30 seconds")
                        result = "Error: Request timed out. Please try again."
                    
            except Exception as e:
                print(f"Error in view: {str(e)}")
                result = f"Error: {str(e)}"

    return render(request, 'searchwithTemple.html', {'result': result})

def index_content():
    index_service = IndexService()

    try:
        index_service.index_reddit_content()
        index_service.index_stackoverflow_content()

        return HttpResponse("Indexing finished.")
    
    except Exception as e:
        logger.error(f"Error during indexing: {str(e)}")
        return HttpResponse(f"Error during indexing: {str(e)}", status=500)
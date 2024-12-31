import concurrent
from django.shortcuts import render
from django.http import HttpResponse
from search.models import RedditContent, StackOverflowContent 



import search.gemini_sample as gs

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
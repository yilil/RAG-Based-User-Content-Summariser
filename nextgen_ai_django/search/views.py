from django.shortcuts import render
from django.http import HttpResponse
from search.models import Document  # Import the Document model

# Create your views here.

import search.gemini_sample as gs

def search(request):
    result = None
    if request.method == "POST":
        search_query = request.POST.get('search_query')

        # # Query the database to find documents where the content contains the search query
        # documents = Document.objects.filter(content__icontains=search_query)  # Case-insensitive match
        # document_data = [
        #     {
        #         "title": doc.title,  # Extract title
        #         "content": doc.content,  # Extract content
        #         "source": doc.source  # Extract source
        #     }
        #     for doc in documents
        # ]

        result = gs.process_search_query(search_query)
        # result = gs.process_search_query(search_query, document_data)
    return render(request, 'search_sample.html', {'result': result})
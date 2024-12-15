from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

import search.gemini_sample as gs

def search(request):
    result = None
    if request.method == "POST":
        search_query = request.POST.get('search_query')
        result = gs.process_search_query(search_query)
    return render(request, 'search_sample.html', {'result': result})
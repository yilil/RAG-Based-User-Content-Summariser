from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from .models import QuestionTemplate
from .forms import QuestionTemplateForm

class QuestionTemplateView:
    def list(request) -> JsonResponse:
        templates = QuestionTemplate.get_all().values()
        return JsonResponse(list(templates), safe=False)

    def create(request) -> JsonResponse:
        if request.method == 'POST':
            form = QuestionTemplateForm(request.POST)
            if form.is_valid():
                template = QuestionTemplate.create_template(form.cleaned_data)
                return JsonResponse({'id': template.id, 'template_text': template.template_text, 'tags': template.tags})
        return JsonResponse({'error': 'Invalid data'}, status=400)

    def update(request, pk) -> JsonResponse:
        if request.method == 'POST':
            form = QuestionTemplateForm(request.POST)
            if form.is_valid():
                template = QuestionTemplate.update_template(pk, form.cleaned_data)
                return JsonResponse({'id': template.id, 'template_text': template.template_text, 'tags': template.tags})
        return JsonResponse({'error': 'Invalid data'}, status=400)

    def delete(request, pk) -> JsonResponse:
        if request.method == 'POST':
            QuestionTemplate.delete_template(pk)
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Invalid request'}, status=400)

    def get_by_id(request, pk) -> JsonResponse:
        template = get_object_or_404(QuestionTemplate, pk=pk)
        return JsonResponse({'id': template.id, 'template_text': template.template_text, 'tags': template.tags})


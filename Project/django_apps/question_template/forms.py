from django import forms
from .models import QuestionTemplate

class QuestionTemplateForm(forms.ModelForm):
    class Meta:
        model = QuestionTemplate
        fields = ['template_text', 'tags']

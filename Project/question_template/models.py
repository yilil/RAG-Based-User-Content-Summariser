from django.db import models

class QuestionTemplate(models.Model):
    template_text = models.TextField()
    tags = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    use_count = models.IntegerField(default=0)

    def __str__(self):
        return self.template_text[:50]

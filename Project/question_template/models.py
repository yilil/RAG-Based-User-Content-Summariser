from django.db import models

class QuestionTemplate(models.Model):
    template_text = models.TextField()
    tags = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    use_count = models.IntegerField(default=0)

    def __str__(self):
        return self.template_text[:50]

    @classmethod
    def get_by_id(cls, pk):
        return cls.objects.get(pk=pk)

    @classmethod
    def get_all(cls):
        return cls.objects.all()

    @classmethod
    def create_template(cls, data):
        return cls.objects.create(**data)

    @classmethod
    def update_template(cls, pk, data):
        template = cls.objects.get(pk=pk)
        for key, value in data.items():
            setattr(template, key, value)
        template.save()
        return template

    @classmethod
    def delete_template(cls, pk):
        template = cls.objects.get(pk=pk)
        template.delete()
        return template

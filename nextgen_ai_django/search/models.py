from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=200)  
    content = models.TextField()  
    embedding = models.JSONField() # e.g. [0.1, 0.2, 0.3, ...]
    source = models.CharField(max_length=50) # e.g. stackoverflow, reddit 
    created_at = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self):
        return self.title

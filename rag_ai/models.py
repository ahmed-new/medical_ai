from django.db import models
from pgvector.django import VectorField
from django.conf import settings

class Chunk(models.Model):
    file_name = models.CharField(max_length=255)
    chunk_index = models.IntegerField()
    content = models.TextField()
    embedding = models.BinaryField()  # هنخزن الـ embedding كـ bytes
    faiss_id = models.IntegerField(null=True, blank=True, db_index=True)

    embedding_vec = VectorField(dimensions=768, null=True, blank=True)

    class Meta:
        unique_together = ("file_name", "chunk_index")  # يمنع التكرار
        indexes = [
            models.Index(fields=["file_name", "chunk_index"]),
            models.Index(fields=["faiss_id"]),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.chunk_index}"







class DailyAIUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_daily_usage")
    date = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date")
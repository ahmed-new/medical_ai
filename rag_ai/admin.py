from django.contrib import admin
from .models import Chunk
import numpy as np

# @admin.register(Chunk)
# class ChunkAdmin(admin.ModelAdmin):
#     list_display = ("file_name", "chunk_index", "short_embedding")
#     search_fields = ("file_name", "content")

#     def short_embedding(self, obj):
#         # نحول الـ bytes لأول 5 قيم Float من الـ embedding
#         try:
#             emb_array = np.frombuffer(obj.embedding, dtype=np.float32)
#             preview = ", ".join([f"{x:.2f}" for x in emb_array[:5]])
#             return f"[{preview} ...]"
#         except:
#             return "N/A"

#     short_embedding.short_description = "Embedding Preview"
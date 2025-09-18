# rag_ai/urls.py
from django.urls import path
from .views import ask_api , chat_ui ,AskApiV1,AskApiV1Simple
urlpatterns = [
    path("api/ask/", ask_api, name="ask_api"),
    path("chat/", chat_ui, name="chat_ui"),
    path("api/v1/ask/", AskApiV1.as_view(), name="ask_api_v1"),# الجديد (للموبايل)
    path("api/v1/ask/simple/", AskApiV1Simple.as_view(), name="ask_api_v1_simple"),
]

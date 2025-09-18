
from django.contrib import admin
from django.urls import path , include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("users.urls")),
    path('', include("rag_ai.urls")),
     path("", include("edu.urls")),

]
from .admin_menu import patch_admin_menu
patch_admin_menu()
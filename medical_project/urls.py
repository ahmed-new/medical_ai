
from django.contrib import admin
from django.urls import path , include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("users.urls")),
    path('', include("rag_ai.urls")),
    path("", include("edu.urls")),

    path("ckeditor/", include("ckeditor_uploader.urls")),
]
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# print(settings.DEFAULT_FILE_STORAGE if hasattr(settings, "DEFAULT_FILE_STORAGE") else "no DEFAULT_FILE_STORAGE")
# print(settings.STORAGES["default"]["BACKEND"])
# print(settings.CKEDITOR_STORAGE_BACKEND)

from .admin_menu import patch_admin_menu
patch_admin_menu()
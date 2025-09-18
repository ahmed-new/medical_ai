# users/urls.py
from django.urls import path
from .views import register, me, login_with_device
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 






urlpatterns = [
    path("auth/register/", register, name="register"),
    path("auth/me/", me, name="me"),






    # JWT:
    path("auth/login/", login_with_device, name="token_obtain_pair_device"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

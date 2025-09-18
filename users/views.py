# users/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, MeSerializer

User = get_user_model()

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    Body: { "username": "", "email": "", "password": "", "study_year": "y1|y2|..." }
    Note: subscription is NOT active; admin must activate later.
    """
    ser = RegisterSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response({"detail": "registered"}, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Returns the current user's profile and subscription status.
    """
    return Response(MeSerializer(request.user).data, status=status.HTTP_200_OK)







# users/views.py (بديل لـ TokenObtainPairView)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.utils import timezone

@api_view(["POST"])
@permission_classes([AllowAny])
def login_with_device(request):
    """
    Body: { "username": "", "password": "", "device_id": "<UUID>" }
    - يربط active_device_id للمستخدم غير الـ superuser في أول تسجيل على جهاز.
    - superuser مستثنى: لا حاجة لـ device_id، ولا ربط.
    """
    username = (request.data.get("username") or "").strip()
    password = (request.data.get("password") or "").strip()
    device_id = (request.data.get("device_id") or "").strip()

    if not username or not password:
        return Response({"detail": "username and password are required"}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    # ✅ superuser: لا نقيّد بجهاز، ولا نطلب device_id
    if user.is_superuser:
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)

    # المستخدم العادي: device_id مطلوب
    if not device_id:
        return Response({"detail": "device_id is required"}, status=400)

    # إن كان مربوطًا بجهاز آخر → ارفض
    if user.active_device_id and user.active_device_id != device_id:
        return Response({"detail": "Account is already active on another device"}, status=409)

    # اربط الجهاز أول مرة
    if not user.active_device_id:
        user.active_device_id = device_id
        user.save(update_fields=["active_device_id"])

    refresh = RefreshToken.for_user(user)
    return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)

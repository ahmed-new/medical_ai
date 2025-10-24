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

# users/views.py
@api_view(["POST"])
@permission_classes([AllowAny])
def login_with_device(request):
    """
    Body: { "username": "", "password": "", "device_id": "<UUID or any string>" }
    سياسة:
    - يُسمح بتسجيل جهازين (device_id_1, device_id_2).
    - active_device_id يُحدَّث عند كل تسجيل دخول إلى الجهاز الحالي.
    - أي طلبات من جهاز غير نشِط تُرفض بواسطة SingleDeviceOnly.
    """
    username = (request.data.get("username") or "").strip()
    password = (request.data.get("password") or "").strip()
    device_id = (request.data.get("device_id") or "").strip()

    if not username or not password:
        return Response({"detail": "username and password are required"}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    # superuser مستثنى من القيد
    if user.is_superuser:
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)

    if not device_id:
        return Response({"detail": "device_id is required"}, status=400)

    # حالياً مسجلين؟
    slot1 = (user.device_id_1 or "").strip()
    slot2 = (user.device_id_2 or "").strip()

    if device_id == slot1 or device_id == slot2:
        # الجهاز معروف — فعّله
        user.active_device_id = device_id
        user.save(update_fields=["active_device_id"])
    else:
        # جهاز جديد
        if not slot1:
            user.device_id_1 = device_id
            user.active_device_id = device_id
            user.save(update_fields=["device_id_1", "active_device_id"])
        elif not slot2:
            user.device_id_2 = device_id
            user.active_device_id = device_id
            user.save(update_fields=["device_id_2", "active_device_id"])
        else:
            # الاتنين مليانين: ارفض أو اعمل سياسة استبدال لاحقاً
            return Response({"detail": "Two devices already registered"}, status=409)

    # اصدار التوكنات
    refresh = RefreshToken.for_user(user)
    return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)


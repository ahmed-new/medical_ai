# users/permissions.py
from rest_framework.permissions import IsAuthenticated

class SingleDeviceOnly(IsAuthenticated):
    """
    يسمح بطلبات من جهاز واحد فقط (بناءً على X-Device-Id)،
    ويستثني superuser من القيد.
    """
    message = "This account is active on another device or X-Device-Id is missing."

    def has_permission(self, request, view):
        ok = super().has_permission(request, view)
        if not ok:
            return False

        user = request.user
        # ✅ superuser مستثنى تمامًا
        if getattr(user, "is_superuser", False):
            return True

        dev = (request.headers.get("X-Device-Id") or "").strip()
        if not dev:
            # لازم العنوان
            return False

        active_dev = (getattr(user, "active_device_id", None) or "").strip()
        if not active_dev:
            # لو لسه مش مربوط (حالة شاذة)، ارفض وخلّي الربط يتم عند تسجيل الدخول
            return False

        return dev == active_dev

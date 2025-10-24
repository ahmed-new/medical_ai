# users/permissions.py
from rest_framework.permissions import IsAuthenticated

# users/permissions.py
class SingleDeviceOnly(IsAuthenticated):
    """
    يسمح بطلبات من جهاز واحد نشِط (active_device_id).
    يُسمح بتخزين جهازين، لكن النشِط فقط هو المسموح له حالياً.
    superuser مستثنى.
    """
    message = "This account is active on another device or X-Device-Id is missing."

    def has_permission(self, request, view):
        ok = super().has_permission(request, view)
        if not ok:
            return False

        user = request.user
        if getattr(user, "is_superuser", False):
            return True

        dev = (request.headers.get("X-Device-Id") or "").strip()
        if not dev:
            return False

        active_dev = (getattr(user, "active_device_id", None) or "").strip()
        return bool(active_dev) and (dev == active_dev)




# class SingleDeviceOnly(IsAuthenticated):
#     message=" you are not allowed to accesess this acount from that device"

#     def has_permission(self, request, view):
#         ok = super().has_perrmssion(request, view)
#         if not ok:
#             return False
        
#         user= request.user
#         if getattr(user , "is_superuser" ,False):
#             return True
        
#         dev = getattr(request.header.get'')
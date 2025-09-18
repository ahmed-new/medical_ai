# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # أعمدة الواجهة الرئيسية
    list_display = ("id", "username", "email", "study_year", "plan",
                    "is_active_subscription" ,"active_device_id", "activated_at","expires_at", "is_staff")
    list_filter = ("plan", "is_active_subscription", "study_year", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    ordering = ("id",)

    # أقسام نموذج التحرير
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email" ,"active_device_id")}),
        ("Study / Subscription", {
            "fields": ("study_year", "plan", "is_active_subscription", "activated_at", "expires_at")
        }),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "study_year"),
        }),
    )

    readonly_fields = ("activated_at", "expires_at" ,"active_device_id")  # بيتحددوا أوتوماتيك لما يتفعّل الاشتراك

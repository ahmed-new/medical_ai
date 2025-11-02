# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # أعمدة الواجهة الرئيسية
    list_display = ("id", "username", "email","phone_number", "study_year", "plan",
                    "is_active_subscription" ,"active_device_id", "activated_at","expires_at", "is_staff")
    list_filter = ("plan", "is_active_subscription", "study_year", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email","phone_number")
    ordering = ("id",)

    # أقسام نموذج التحرير
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email" ,"phone_number","active_device_id","device_id_1","device_id_2",)}),
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















from django.contrib import admin
from .models import Plan, Coupon, Subscription


# ---------- Plan ----------
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_egp", "duration_days", "is_active")
    list_editable = ("price_egp", "duration_days", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("price_egp",)


# ---------- Coupon ----------
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent", "usage_progress", "is_active", "valid_from", "valid_to")
    list_editable = ("percent", "is_active")
    search_fields = ("code",)
    list_filter = ("is_active",)
    ordering = ("-is_active", "code")

    @admin.display(description="Usage")
    def usage_progress(self, obj: Coupon):
        if obj.max_uses_total is None:
            return f"{obj.used_count_total} / ∞"
        return f"{obj.used_count_total} / {obj.max_uses_total}"


# ---------- Subscription ----------
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "is_trial", "started_at", "ends_at", "final_price_egp", "coupon_code")
    list_filter = ("status", "is_trial", "plan")
    search_fields = ("user__username", "user__email", "plan__code", "coupon_code")
    ordering = ("-started_at",)
    autocomplete_fields = ("user", "plan")
    actions = ("mark_as_expired",)

    @admin.action(description="Mark selected as EXPIRED")
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status=Subscription.Status.EXPIRED)
        self.message_user(request, f"{updated} subscription(s) marked as EXPIRED.")

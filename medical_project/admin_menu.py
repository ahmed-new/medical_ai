# project/admin_menu.py
from django.contrib import admin

# 1) عناوين الأدمن
admin.site.site_header = "AXONELIX MEDICAL HUB"
admin.site.site_title  = "AXONELIX MEDICAL HUB"
admin.site.index_title = "Administration"

# 2) ترتيب التطبيقات (labels) — اختياري
APP_ORDER = [
    "users",
    "edu",
    "rag_ai",
    "auth",
    "sessions",
    "admin",
]

# 3) ترتيب الموديلات داخل كل تطبيق (object_name = اسم الكلاس)
MODEL_ORDER = {
    "edu": [
        "Year",
        "Semester",
        "Module",
        "Subject",
        "Lesson",
        "Question",
        "QuestionOption",
        "FlashCard",
        "FavoriteLesson",
    ],
    "rag_ai": [
        "DailyAIUsage",
        # لو عندك موديلات تانية في rag_ai ضيفها هنا
    ],
    "users": [
        "User",
        # لو عندك موديلات إضافية في users ضيفها
    ],
    # ممكن ترتّب "auth" كمان لو حابب
    "auth": [
        "Group",
        "Permission",
    ],
}

def _app_order_key(app):
    label = app["app_label"]
    try:
        return APP_ORDER.index(label)
    except ValueError:
        return 999  # أي تطبيق مش متسجّل في APP_ORDER يروح آخر القائمة

def _custom_get_app_list(self, request):
    """
    نرتب التطبيقات حسب APP_ORDER، والموديلات داخل كل تطبيق حسب MODEL_ORDER.
    """
    app_dict = self._build_app_dict(request)
    app_list = sorted(app_dict.values(), key=_app_order_key)

    for app in app_list:
        label = app["app_label"]
        desired = MODEL_ORDER.get(label)

        if desired:
            app["models"].sort(
                key=lambda m: desired.index(m["object_name"]) if m["object_name"] in desired else len(desired) + 1
            )
        else:
            # الافتراضي: ترتيب أبجدي بالاسم المعروض
            app["models"].sort(key=lambda m: m["name"])

    return app_list

def patch_admin_menu():
    # طبّق الباتش
    admin.AdminSite.get_app_list = _custom_get_app_list

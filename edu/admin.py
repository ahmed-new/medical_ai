from django.contrib import admin
from .models import Year, Semester, Module, Subject, Lesson,Question, QuestionOption,FlashCard
from django import forms
from ckeditor.widgets import CKEditorWidget


# ---- أساسيات الجداول الهرمية ----
@admin.register(Year)
class YearAdmin(admin.ModelAdmin):
    list_display  = ("name", "code", "order", "id")
    list_editable = ("order",)
    search_fields = ("name", "code")
    ordering      = ("order", "id")

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display  = ("name", "year", "order", "id")
    list_filter   = ("year",)
    list_editable = ("order",)
    search_fields = ("name",)
    ordering      = ("year__order", "order", "id")
    autocomplete_fields = ("year",)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display  = ("name", "semester", "order", "id")
    list_filter   = ("semester__year", "semester")
    list_editable = ("order",)
    search_fields = ("name",)
    ordering      = ("semester__year__order", "semester__order", "order", "id")
    autocomplete_fields = ("semester",)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ("name", "module", "order", "id")
    list_filter   = ("module__semester__year", "module")
    list_editable = ("order",)
    search_fields = ("name",)
    ordering      = ("module__semester__year__order", "module__semester__order", "module__order", "order", "id")
    autocomplete_fields = ("module",)

class LessonAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget(config_name="default"), required=False)
    class Meta:
        model = Lesson
        fields = "__all__"

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = LessonAdminForm
    list_display  = ("title", "subject", "order", "id")
    list_filter   = ("subject__module__semester__year", "subject__module", "subject")
    list_editable = ("order",)
    search_fields = ("title", "content")
    ordering      = ("subject__module__semester__year__order",
                     "subject__module__semester__order",
                     "subject__module__order",
                     "subject__order", "order", "id")
    autocomplete_fields = ("subject",)






class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4   # يظهر 4 حقول افتراضيًا
    min_num = 4
    max_num = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question_type", "source_type", "exam_kind", "year", "subject", "lesson")
    list_filter = ("question_type", "source_type", "exam_kind", "year", "subject", "lesson")
    search_fields = ("text",)
    inlines = [QuestionOptionInline]
    fieldsets = (
        (None, {
            "fields": (
                "text", "question_type", "source_type",
                "year","module", "subject", "lesson",
                "exam_kind", "exam_year", "grade",
                "answer_text", "explanation"
            )
        }),
    )












# ---- FlashCard Admin ----
class FlashCardAdminForm(forms.ModelForm):
    class Meta:
        model = FlashCard
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        owner_type = cleaned.get("owner_type")
        owner      = cleaned.get("owner")

        # لازم lesson أو subject
        if not cleaned.get("lesson") and not cleaned.get("subject"):
            raise forms.ValidationError("Provide at least one of lesson or subject.")

        # لو admin → امسح المالك
        if owner_type == "admin":
            cleaned["owner"] = None
        # لو user → لازم owner
        elif owner_type == "user" and not owner:
            raise forms.ValidationError("User-owned flashcard must have an owner.")
        return cleaned


@admin.register(FlashCard)
class FlashCardAdmin(admin.ModelAdmin):
    form = FlashCardAdminForm

    list_display  = ("short_q", "owner_type", "owner", "lesson", "subject", "order", "updated_at", "id")
    list_filter   = (
        "owner_type",
        ("lesson", admin.RelatedOnlyFieldListFilter),
        ("subject", admin.RelatedOnlyFieldListFilter),
        ("lesson__subject__module__semester__year", admin.RelatedOnlyFieldListFilter),
        ("subject__module__semester__year", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = ("question", "answer")
    ordering      = ("order", "-updated_at", "-id")

    autocomplete_fields = ("lesson", "subject", "owner")
    list_editable       = ("order",)
    readonly_fields     = ("updated_at", "created_at")

    fieldsets = (
        ("Link", {"fields": ("lesson", "subject")}),
        ("Ownership", {"fields": ("owner_type", "owner")}),
        ("Content", {"fields": ("question", "answer")}),
        ("Meta", {"fields": ("order", "created_at", "updated_at")}),
    )

    def short_q(self, obj):
        return (obj.question or "")[:60]
    short_q.short_description = "Question"

    # سياسات إضافية: الموظف غير السوبر ماينفعش يعمل admin-card
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        # اسمح للسوبر يحرر كل حاجة
        if request.user.is_superuser:
            return ro
        # غير السوبر: امنع تغيير owner_type لغير user
        ro.append("owner_type")
        return tuple(ro)

    def save_model(self, request, obj, form, change):
        # غير السوبر → اجبر owner_type=user
        if not request.user.is_superuser:
            obj.owner_type = "user"
            if not obj.owner:
                obj.owner = request.user  # أو سيبها None ويترفض بالتحقق
        # admin-card: owner = None
        if obj.owner_type == "admin":
            obj.owner = None
        super().save_model(request, obj, form, change)




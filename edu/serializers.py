# edu/serializers.py
from rest_framework import serializers
from .models import Year, Semester, Module, Subject, Lesson ,Question, QuestionOption,FlashCard,FavoriteLesson ,PlannerTask

class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ["id", "code", "name", "order"]

class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ["id", "name", "order", "year"]

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "name", "order", "semester"]

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "order", "module"]



class LessonSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "order", "subject", "part_type", "pdf_url"]

    def get_pdf_url(self, obj):
        return obj.pdf.url if obj.pdf else None




class QuestionLiteSerializer(serializers.ModelSerializer):
    has_options = serializers.SerializerMethodField()


    class Meta:
        model = Question
        fields = ["id", "question_type", "source_type", "part_type", "text", "has_options"]

    def get_has_options(self, obj):
        return obj.options.exists()

class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "text"]  # لا نعرض is_correct للطالب

class QuestionDetailSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)


    class Meta:
        model = Question
        fields = ["id", "question_type", "source_type", "text", "image", "options"]

    def get_options(self, obj):
        if obj.question_type == "mcq":
            return QuestionOptionSerializer(obj.options.all(), many=True).data
        return []





class LessonLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "subject"]



class FlashCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashCard
        fields = ["id", "owner_type", "lesson", "subject", "question", "answer", "order",
                  "created_at", "updated_at"]

class FlashCardCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashCard
        fields = ["lesson", "subject", "question", "answer", "order"]

    def validate(self, data):
        # لازم واحد على الأقل: lesson أو subject
        if not data.get("lesson") and not data.get("subject"):
            raise serializers.ValidationError("Provide at least lesson or subject.")
        return data
    



class FavoriteLessonSerializer(serializers.ModelSerializer):
    # نرجّع الدرس كـ Lite
    lesson = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteLesson
        fields = ["id", "lesson", "created_at"]

    def get_lesson(self, obj):
        from .serializers import LessonLiteSerializer
        return LessonLiteSerializer(obj.lesson).data
    



class PlannerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlannerTask
        fields = ["id", "title", "notes", "due_date", "is_done", "user"]
        read_only_fields = ["user"]
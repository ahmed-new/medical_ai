# edu/serializers.py
from rest_framework import serializers
from .models import Year, Semester, Module, Subject, Chapter,Lesson ,Question, QuestionOption,FlashCard,FavoriteLesson ,PlannerTask,StudySession,LessonProgress

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



class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "title", "order", "subject"]





class LessonSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    chapter = ChapterSerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "order", "subject", "part_type", "chapter", "pdf_url"]

    def get_pdf_url(self, obj):
        return obj.pdf.url if obj.pdf else None




class QuestionLiteSerializer(serializers.ModelSerializer):
    has_options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "question_type",
            "source_type",
            "part_type",
            "text",
            "is_tbl",        # NEW
            "is_flipped",    # NEW
            "has_options",
        ]

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
        fields = ["id", "question_type", "source_type", "text", "image",
            "is_tbl",       
            "is_flipped",  "options"]
        

    def get_options(self, obj):
        if obj.question_type == "mcq":
            return QuestionOptionSerializer(obj.options.all(), many=True).data
        return []





class LessonLiteSerializer(serializers.ModelSerializer):
    chapter = serializers.SerializerMethodField()
    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "part_type", "chapter", "subject"]

    def get_chapter(self, obj):
        if obj.chapter_id:
            return {"id": obj.chapter_id, "title": obj.chapter.title, "order": obj.chapter.order}
        return None
    
    

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
        """
        لو إنشاء جديد: لازم يبقى فيه lesson أو subject.
        لو تعديل (instance موجود): نسمح إنهم مايجوش فى الـ data
        ونستخدم القيم اللى فى الـ instance.
        """
        lesson  = data.get("lesson")  or getattr(self.instance, "lesson", None)
        subject = data.get("subject") or getattr(self.instance, "subject", None)

        if not lesson and not subject:
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
        
        
        
        

class StudySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StudySession
        fields = ["id","started_at","minutes","source","created_at"]



class QuestionAttemptCreateSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField(required=True)




class LessonProgressSerializer(serializers.ModelSerializer):
    # نرجّع الدرس كـ Lite زي الـ FavoriteLessonSerializer
    lesson = serializers.SerializerMethodField()

    class Meta:
        model = LessonProgress
        fields = ["id", "lesson", "created_at"]

    def get_lesson(self, obj):
        from .serializers import LessonLiteSerializer
        return LessonLiteSerializer(obj.lesson).data
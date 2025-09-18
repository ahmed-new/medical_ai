# edu/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .policy import can_view_questions, sources_allowed ,can_view_lesson_content ,flashcard_visibility_q 
from .models import Year, Semester, Module, Subject, Lesson ,Question ,FlashCard,FavoriteLesson
from .serializers import (
    YearSerializer, SemesterSerializer, ModuleSerializer,
    SubjectSerializer, LessonSerializer ,QuestionLiteSerializer ,QuestionDetailSerializer,LessonLiteSerializer,
    FlashCardSerializer,FlashCardCreateUpdateSerializer ,FavoriteLessonSerializer
)
from users.permissions import SingleDeviceOnly






def _get_user_year(request):
    code = (getattr(request.user, "study_year", None) or "").strip()
    if not code:
        return None
    try:
        return Year.objects.get(code=code)
    except Year.DoesNotExist:
        return None

class YearMe(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response({"detail": "No study_year set for user"}, status=404)
        return Response(YearSerializer(year).data, status=200)

class StudentSemesters(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response([], status=200)
        qs = Semester.objects.filter(year=year).order_by("order","id")
        return Response(SemesterSerializer(qs, many=True).data, status=200)

class StudentModules(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response([], status=200)

        semester_id = request.query_params.get("semester_id")
        qs = Module.objects.filter(semester__year=year)
        if semester_id:
            qs = qs.filter(semester_id=semester_id, semester__year=year)
        qs = qs.order_by("order","id")
        return Response(ModuleSerializer(qs, many=True).data, status=200)

class StudentSubjects(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response([], status=200)

        module_id = request.query_params.get("module_id")
        qs = Subject.objects.filter(module__semester__year=year)
        if module_id:
            qs = qs.filter(module_id=module_id, module__semester__year=year)
        qs = qs.order_by("order","id")
        return Response(SubjectSerializer(qs, many=True).data, status=200)

class StudentLessons(APIView):
    """
    قائمة الدروس لمادة معيّنة (subject_id) أو لكل مواد سنة الطالب.
    مبدئيًا نرجّع العناوين + المحتوى. لو عايز نسخة مختصرة بدون content نضيف Serializer Lite لاحقًا.
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response([], status=200)

        subject_id = request.query_params.get("subject_id")
        qs = Lesson.objects.filter(subject__module__semester__year=year)
        if subject_id:
            qs = qs.filter(subject_id=subject_id, subject__module__semester__year=year)
        qs = qs.order_by("order","id")
        return Response(LessonLiteSerializer(qs, many=True).data, status=200)




class LessonDetail(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]
    def get(self, request, pk: int):
        year = _get_user_year(request)
        if not year:
            return Response({"detail": "Lesson not found"}, status=404)
        try:
            obj = Lesson.objects.get(pk=pk, subject__module__semester__year=year)
        except Lesson.DoesNotExist:
            return Response({"detail": "Lesson not found"}, status=404)

        # ✅ منع رؤية المحتوى لو الخطة none أو الاشتراك غير مفعّل
        if not can_view_lesson_content(request.user):
            # نرجّع Basic info فقط أو رسالة منع
            # هنا نفضل إرجاع 402 مع معلومات مختصرة بدون content
            lite = LessonLiteSerializer(obj).data
            return Response(
                {
                    "detail": "Subscription required to view lesson content.",
                    "lesson": lite
                },
                status=402  # Payment Required
            )

        # ✅ المصرّح لهم يشوفوا كامل التفاصيل (بما فيها content)
        return Response(LessonSerializer(obj).data, status=200)















class StudentQuestions(APIView):
    """
    GET /api/v1/edu/questions/?lesson_id=&subject_id=&module_id=&limit=&offset=
    - يُرجع أسئلة الطالب وفق سنّته وبحسب الباقة:
        * basic:     qbank فقط
        * premium:   qbank + exam_review
        * advanced:  الكل
    - Pagination بسيطة عبر limit/offset.
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def get(self, request):
        # صلاحية عرض الأسئلة حسب الباقة والاشتراك
        if not can_view_questions(request.user):
            return Response({"detail": "Questions are not available for your current plan/subscription."}, status=403)

        year = _get_user_year(request)
        if not year:
            return Response({"detail": "No study year set for user."}, status=400)

        # نطاق السؤال
        lesson_id  = request.query_params.get("lesson_id")
        subject_id = request.query_params.get("subject_id")
        module_id  = request.query_params.get("module_id")

        qs = Question.objects.all()

        # قصر حسب سنّة المستخدم
        # لو السؤال مرتبط بـ lesson/subject/module/year فهنقصر accordingly
        # (هنا نفترض إن بياناتك بتُملأ صح في واحد من الحقول دي)
        q_filters = Q()
        q_filters |= Q(lesson__subject__module__semester__year=year)
        q_filters |= Q(subject__module__semester__year=year)
        q_filters |= Q(module__semester__year=year)
        q_filters |= Q(year__code=year.code)
        qs = qs.filter(q_filters)

        # فلاتر اختيارية
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        elif subject_id:
            qs = qs.filter(subject_id=subject_id)
        elif module_id:
            qs = qs.filter(module_id=module_id)

        # قصر حسب مصادر الباقة
        allowed = list(sources_allowed(request.user))
        qs = qs.filter(source_type__in=allowed).order_by("id")

        # Pagination بسيطة
        try:
            limit = max(1, min(int(request.query_params.get("limit", 20)), 100))
        except Exception:
            limit = 20
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except Exception:
            offset = 0

        total = qs.count()
        items = qs[offset:offset+limit]
        data = QuestionLiteSerializer(items, many=True).data

        return Response({
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": data,
        }, status=200)

class StudentQuestionDetail(APIView):
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def get(self, request, pk: int):
        if not can_view_questions(request.user):
            return Response({"detail": "Questions are not available for your current plan/subscription."}, status=403)

        year = _get_user_year(request)
        if not year:
            return Response({"detail": "No study year set for user."}, status=400)

        try:
            obj = (Question.objects
                   .filter(
                        Q(lesson__subject__module__semester__year=year) |
                        Q(subject__module__semester__year=year) |
                        Q(module__semester__year=year) |
                        Q(year__code=year.code),
                        source_type__in=list(sources_allowed(request.user))
                    )
                   .get(pk=pk))
        except Question.DoesNotExist:
            return Response({"detail": "Question not found"}, status=404)

        return Response(QuestionDetailSerializer(obj).data, status=200)
    







# flash cards logic
class FlashCardListCreate(APIView):
    """
    GET /api/v1/edu/flashcards/?lesson_id=&subject_id=
      - يرجّع Admin + كروت الطالب نفسه فقط
      - مفلترة على سنة الطالب عبر lesson/subject->...->Year

    POST /api/v1/edu/flashcards/
      - ينشئ كارت خاص بالطالب (owner_type=user, owner=request.user)
      Body: { question, answer?, lesson_id?, subject_id?, order? }
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response([], status=200)

        lesson_id  = request.query_params.get("lesson_id")
        subject_id = request.query_params.get("subject_id")

        qs = FlashCard.objects.all()

        # قصر على سنة الطالب عبر علاقات lesson/subject
        year_filter = (
            Q(lesson__subject__module__semester__year=year) |
            Q(subject__module__semester__year=year)
        )
        qs = qs.filter(year_filter)

        # فلاتر سياقية
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        # ✅ سياسة الرؤية حسب الخطة
        qs = qs.filter(flashcard_visibility_q(request.user))

        qs = qs.order_by("order", "-updated_at", "-id")[:200]
        return Response(FlashCardSerializer(qs, many=True).data, status=200)





    def post(self, request):
        data = request.data.copy()
        # السماح بتمرير lesson_id/subject_id بالأرقام
        data["owner_type"] = "user"

        ser = FlashCardCreateUpdateSerializer(data=data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        # تحقق السنة
        lesson = ser.validated_data.get("lesson")
        subject = ser.validated_data.get("subject")
        year = _get_user_year(request)
        if not year:
            return Response({"detail": "Year not set for user"}, status=400)

        if lesson and lesson.subject.module.semester.year_id != year.id:
            return Response({"detail": "Lesson not in your year"}, status=403)
        if subject and subject.module.semester.year_id != year.id:
            return Response({"detail": "Subject not in your year"}, status=403)

        fc = FlashCard.objects.create(
            owner_type="user",
            owner=request.user,
            lesson=lesson,
            subject=subject,
            question=ser.validated_data["question"].strip(),
            answer=(ser.validated_data.get("answer") or "").strip(),
            order=ser.validated_data.get("order") or 1,
        )
        return Response({"id": fc.id}, status=201)







class FlashCardDetail(APIView):
    """
    PUT /api/v1/edu/flashcards/<id>/
    DELETE /api/v1/edu/flashcards/<id>/
    - الطالب يعدّل/يحذف كروته فقط (owner_type=user, owner=himself)
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def put(self, request, pk: int):
        try:
            fc = FlashCard.objects.get(pk=pk, owner_type="user", owner=request.user)
        except FlashCard.DoesNotExist:
            return Response({"detail": "not found or not your card"}, status=404)

        ser = FlashCardCreateUpdateSerializer(fc, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        # تأكيد بقاء الربط داخل نفس السنة
        lesson = ser.validated_data.get("lesson", fc.lesson)
        subject = ser.validated_data.get("subject", fc.subject)
        year = _get_user_year(request)
        if not year:
            return Response({"detail": "Year not set for user"}, status=400)

        if lesson and lesson.subject.module.semester.year_id != year.id:
            return Response({"detail": "Lesson not in your year"}, status=403)
        if subject and subject.module.semester.year_id != year.id:
            return Response({"detail": "Subject not in your year"}, status=403)

        fc.lesson   = lesson
        fc.subject  = subject
        if "question" in ser.validated_data:
            fc.question = ser.validated_data["question"].strip()
        if "answer" in ser.validated_data:
            fc.answer   = (ser.validated_data.get("answer") or "").strip()
        if "order" in ser.validated_data:
            fc.order    = ser.validated_data.get("order") or fc.order
        fc.save()
        return Response({"detail": "updated"}, status=200)

    def delete(self, request, pk: int):
        deleted, _ = FlashCard.objects.filter(pk=pk, owner_type="user", owner=request.user).delete()
        if deleted:
            return Response({"detail": "deleted"}, status=200)
        return Response({"detail": "not found or not your card"}, status=404)





# favorit lessons logic


class FavoriteLessonList(APIView):
    """
    GET /api/v1/edu/favorites/lessons/?limit=&offset=
    - يرجّع مفضلات الطالب (دروس فقط) ضمن سنّته.
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response({"total": 0, "items": []}, status=200)

        qs = (FavoriteLesson.objects
              .filter(user=request.user,
                      lesson__subject__module__semester__year=year))

        # pagination البسيطة
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except Exception:
            limit = 50
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except Exception:
            offset = 0

        total = qs.count()
        items = qs.select_related("lesson", "lesson__subject").order_by("-created_at", "-id")[offset:offset+limit]
        data = FavoriteLessonSerializer(items, many=True).data
        return Response({"total": total, "limit": limit, "offset": offset, "items": data}, status=200)

class FavoriteLessonIDs(APIView):
    """
    GET /api/v1/edu/favorites/lessons/ids/
    - يرجّع IDs فقط لتظليل الأيقونة في الواجهة بسهولة.
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def get(self, request):
        year = _get_user_year(request)
        if not year:
            return Response({"ids": []}, status=200)

        ids = (FavoriteLesson.objects
               .filter(user=request.user,
                       lesson__subject__module__semester__year=year)
               .values_list("lesson_id", flat=True))
        return Response({"ids": list(ids)}, status=200)

class FavoriteLessonAdd(APIView):
    """
    POST /api/v1/edu/favorites/lessons/
    Body: { "lesson": <id> }
    - يضيف درس إلى المفضلة (idempotent).
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def post(self, request):
        try:
            lesson_id = int(request.data.get("lesson"))
        except Exception:
            return Response({"detail": "lesson is required and must be int"}, status=400)

        year = _get_user_year(request)
        if not year:
            return Response({"detail": "No study year set for user"}, status=400)

        try:
            lesson = Lesson.objects.get(pk=lesson_id, subject__module__semester__year=year)
        except Lesson.DoesNotExist:
            return Response({"detail": "Lesson not found in your year"}, status=404)

        obj, created = FavoriteLesson.objects.get_or_create(user=request.user, lesson=lesson)
        return Response({"id": obj.id, "created": created}, status=201 if created else 200)

class FavoriteLessonRemove(APIView):
    """
    DELETE /api/v1/edu/favorites/lessons/
    Query: ?lesson=<id>
    - يحذف مفضلة الدرس (idempotent).
    """
    permission_classes = [IsAuthenticated, SingleDeviceOnly]

    def delete(self, request):
        lesson_id = request.query_params.get("lesson")
        if not lesson_id:
            return Response({"detail": "lesson query param is required"}, status=400)

        year = _get_user_year(request)
        if not year:
            return Response({"detail": "No study year set for user"}, status=400)

        deleted, _ = (FavoriteLesson.objects
                      .filter(user=request.user,
                              lesson_id=lesson_id,
                              lesson__subject__module__semester__year=year)
                      .delete())
        return Response({"deleted": bool(deleted)}, status=200)
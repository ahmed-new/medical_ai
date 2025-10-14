# edu/models.py
from django.db import models
from cloudinary_storage.storage import RawMediaCloudinaryStorage,MediaCloudinaryStorage
from django.core.validators import FileExtensionValidator



class Year(models.Model):
    class Code(models.TextChoices):
        Y1 = "y1", "Year 1"
        Y2 = "y2", "Year 2"
        Y3 = "y3", "Year 3"
        Y4 = "y4", "Year 4"
        Y5 = "y5", "Year 5"

    code  = models.CharField(
        max_length=10,
        choices=Code.choices,
        unique=True,
        db_index=True,
        
    )
    name  = models.CharField(
        max_length=100,
        unique=True,
        
    )
    order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.code})"



class Semester(models.Model):
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name="semesters")
    name = models.CharField(max_length=100)               # مثال: "Semester 1"
    order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        unique_together = ("year", "name")
        ordering = ["year__order", "order", "id"]

    def __str__(self):
        return f"{self.year} / {self.name}"


class Module(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="modules")
    name = models.CharField(max_length=150)               # مثال: "Cardiovascular Module"
    order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        unique_together = ("semester", "name")
        ordering = ["semester__year__order", "semester__order", "order", "id"]

    def __str__(self):
        return f"{self.semester} / {self.name}"


class Subject(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=150)               # مثال: "Internal Medicine"
    order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        unique_together = ("module", "name")
        ordering = ["module__semester__year__order", "module__semester__order", "module__order", "order", "id"]

    def __str__(self):
        return f"{self.module} / {self.name}"





class Chapter(models.Model):
    subject = models.ForeignKey("Subject", on_delete=models.CASCADE, related_name="chapters", db_index=True)
    title   = models.CharField(max_length=255)
    order   = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        ordering = ("subject_id", "order", "id")
        constraints = [
            models.UniqueConstraint(fields=["subject", "order"], name="uq_chapter_subject_order"),
        ]

    def __str__(self):
        return f"{self.subject} · {self.title}"















class PartType(models.TextChoices):
        THEORETICAL = "theoretical", "Theoretical"
        PRACTICAL   = "practical",  "Practical"


class Lesson(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="lessons")
    chapter = models.ForeignKey("Chapter", on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons", db_index=True)
    part_type = models.CharField(
        max_length=20, choices=PartType.choices, default=PartType.THEORETICAL, db_index=True
     )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True) 
    pdf = models.FileField(
        upload_to="lesson_pdfs/%Y/%m/%d/",
        storage=RawMediaCloudinaryStorage(),                # يرفع على raw/
        validators=[FileExtensionValidator(["pdf"])],
        blank=True, null=True,
    ) 
    order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        unique_together = ("subject", "title")
        ordering = [
            "subject__module__semester__year__order",
            "subject__module__semester__order",
            "subject__module__order",
            "subject__order",
            "order",
            "id",
        ]

    def __str__(self):
        return f"{self.subject} / {self.title}"


from django.conf import settings

class LessonProgress(models.Model):
    user   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey("edu.Lesson", on_delete=models.CASCADE, related_name="progress")
    is_done = models.BooleanField(default=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "lesson")
        indexes = [
            models.Index(fields=["user", "lesson"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.lesson} (done={self.is_done})"




class PlannerTask(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="planner_tasks")
    title     = models.CharField(max_length=200)
    notes     = models.TextField(blank=True)
    due_date  = models.DateField()              # تاريخ فقط
    is_done   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "due_date", "is_done"])]
        ordering = ["is_done", "due_date", "-id"]


















from django.conf import settings
class FlashCard(models.Model):
    class OwnerType(models.TextChoices):
        ADMIN = "admin", "Admin"
        USER  = "user",  "User"

    # روابط اختيارية (يفضل تربط بواحد فقط، لكن هندعم الاثنين)
    lesson  = models.ForeignKey("edu.Lesson", on_delete=models.CASCADE, related_name="flashcards",
                                null=True, blank=True)
    subject = models.ForeignKey("edu.Subject", on_delete=models.CASCADE, related_name="flashcards",
                                null=True, blank=True)

    owner_type = models.CharField(max_length=10, choices=OwnerType.choices, db_index=True)
    owner      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   null=True, blank=True, related_name="my_flashcards")

    question = models.TextField()
    answer   = models.TextField(blank=True)

    order      = models.PositiveIntegerField(default=1, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-updated_at", "-id"]
        indexes = [
        models.Index(fields=["owner_type", "owner"]),
         ]

    def __str__(self):
        who = "Admin" if self.owner_type == "admin" else f"User:{self.owner_id}"
        target = self.lesson_id or self.subject_id or "-"
        return f"[{who}] FC->{target}: {self.question[:40]}"















class Question(models.Model):
    class QuestionType(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        WRITTEN = "written", "Written"

    class SourceType(models.TextChoices):
        QBANK = "qbank", "Q Bank"
        EXAM_REVIEW = "exam_review", "Exam Review"
        # TBL = "tbl", "TBL"
        # FLIPPED = "flipped", "Flipped"
        OLD_EXAM = "old_exam", "Old Exam"

    class ExamKind(models.TextChoices):
        NONE = "none", "Not Exam"
        MIDTERM = "midterm", "Midterm"
        FINAL = "final", "Final"

    class Grade(models.TextChoices):
        NA = "na", "Not Applicable"
        A = "a", "Grade A"
        B = "b", "Grade B"
        C = "c", "Grade C"

    # Relations
    year = models.ForeignKey(
        "edu.Year",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="questions",
        help_text="Use when the question is linked to a full Year (Exam Review or Old Exam)."
    )
    module = models.ForeignKey(
        "edu.Module",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="questions",
        help_text="Link here if the question belongs to a Module (Exam Review or Old Exam)."
        )
    subject = models.ForeignKey(
        "edu.Subject",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="questions",
        help_text="Use when the question is linked to a Subject (Exam Review, TBL, or Flipped)."
    )
    
    part_type = models.CharField(
        max_length=20, choices=PartType.choices, default=PartType.THEORETICAL, db_index=True
     )
    lesson = models.ForeignKey(
        "edu.Lesson",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="questions",
        help_text="Use when the question is linked to a Lesson (QBank or TBL/Flipped)."
    )

    is_tbl = models.BooleanField(default=False)
    is_flipped = models.BooleanField(default=False)
    
    # Basic data
    text = models.TextField(help_text="The main text of the question as shown to the student.")
    image = models.ImageField(
    upload_to="question_images/%Y/%m/%d/",
    storage=MediaCloudinaryStorage(),
    validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    blank=True,
    null=True,
    help_text="optional : image with question"
)

    question_type = models.CharField(
        max_length=20, choices=QuestionType.choices,
        help_text="Type of the question: MCQ (multiple choice) or Written (open text)."
    )
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices,
        help_text="Source of the question: QBank, Exam Review, TBL, Flipped, Old Exam."
    )

    # Exam-specific
    exam_kind = models.CharField(
        max_length=10,
        choices=ExamKind.choices,
        default=ExamKind.NONE,
        help_text="Required only if the question belongs to an Exam (Midterm/Final)."
    )
    exam_year = models.CharField(
        max_length=20,
        blank=True, null=True,
        help_text="Specify the year of the exam (e.g., 2021) if the source is Exam Review or Old Exam."
    )
    grade = models.CharField(
        max_length=2,
        choices=Grade.choices,
        default=Grade.NA,
        help_text="Required only if the question is from Old Exam, to specify grade (A/B/C)."
    )

    # Answers
    answer_text = models.TextField(
        blank=True, null=True,
        help_text="Model answer text if the question is Written type."
    )
    explanation = models.TextField(
        blank=True, null=True,
        help_text="Explanation of the correct answer (optional, shown after solving)."
    )

    created_at = models.DateTimeField(auto_now_add=True)



    def __str__(self):
        return f"{self.get_question_type_display()} | {self.get_source_type_display()} | {self.text[:50]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Option for Q{self.question.id}: {self.text[:30]}{' ✅' if self.is_correct else ''}"













class FavoriteLesson(models.Model):
    user   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_lessons")
    lesson = models.ForeignKey("edu.Lesson", on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "lesson")
        indexes = [
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["user", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user_id} ♥ {self.lesson_id}"
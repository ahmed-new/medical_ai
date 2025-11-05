from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


phone_validator = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message="Phone must be 7–15 digits, optional leading +.",
)


class User(AbstractUser):
    class StudyYear(models.TextChoices):
        Y1 = "y1", "Year 1"
        Y2 = "y2", "Year 2"
        Y3 = "y3", "Year 3"
        Y4 = "y4", "Year 4"
        Y5 = "y5", "Year 5"

    class Plan(models.TextChoices):
        NONE    = "none",    "No Plan"
        BASIC   = "basic",   "Basic"
        PREMIUM = "premium", "Premium"
        ADVANCED = "advanced", "Advanced"

      # NEW: رقم موبايل اختياري
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, db_index=True,
        validators=[phone_validator]
    )
    
    study_year = models.CharField(max_length=10, choices=StudyYear.choices, null=True, blank=True)
    plan       = models.CharField(max_length=10, choices=Plan.choices, default=Plan.NONE, db_index=True)
    is_active_subscription = models.BooleanField(default=False, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateTimeField(null=True, blank=True)
    device_id_1 = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    device_id_2 = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    active_device_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)  # ✅ جديد

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = self.phone_number.strip().replace(" ", "")
            
        if self.is_active_subscription and not self.activated_at:
            # لو أول مرة يتفعّل
            self.activated_at = timezone.now()
            self.expires_at = self.activated_at + timedelta(days=365)
        super().save(*args, **kwargs)




class Plan(models.Model):
    """
    باقات بالجنيه ومدّة بالأيام.
    """
    code = models.CharField(max_length=32, choices=User.Plan.choices, unique=True, db_index=True)
    name = models.CharField(max_length=64)
    price_egp = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField(default=365)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Coupon(models.Model):
    """
    خصم بالنسبة المئوية فقط + حدود استخدام.
    """
    code = models.CharField(max_length=32, unique=True, db_index=True)  # مثال: SAVE20
    percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # الصلاحية الزمنية (اختياري)
    valid_from = models.DateTimeField(blank=True, null=True)
    valid_to   = models.DateTimeField(blank=True, null=True)
    is_active  = models.BooleanField(default=True, db_index=True)

    # حدود الاستخدام
    max_uses_total   = models.PositiveIntegerField(blank=True, null=True)  # None = غير محدود
    used_count_total = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.code} (-{self.percent}%)"

    def is_valid_now(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.max_uses_total is not None and self.used_count_total >= self.max_uses_total:
            return False
        return True



# users/models.py (أو حيث يوجد Subscription)
class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIAL    = "trial", "Trial"
        ACTIVE   = "active", "Active"
        EXPIRED  = "expired", "Expired"
        PENDING  = "pending", "Pending"   # الجديد

    user  = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="subscriptions", db_index=True)
    plan  = models.ForeignKey(Plan, on_delete=models.PROTECT)
    payment = models.OneToOneField("Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="subscription")  # للربط

    status    = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    is_trial  = models.BooleanField(default=False, db_index=True)

    started_at = models.DateTimeField(null=True, blank=True)  # كان default=timezone.now
    ends_at    = models.DateTimeField(null=True, blank=True)  # كان required

    coupon_code     = models.CharField(max_length=32, blank=True, null=True)
    final_price_egp = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))

    @property
    def is_active_now(self):
        return (
            self.status in (self.Status.TRIAL, self.Status.ACTIVE)
            and self.ends_at is not None
            and self.ends_at >= timezone.now()
        )






class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    discount_code = models.CharField(max_length=50, blank=True, null=True)
    final_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # هذا هو الكود الذي يكتبه الطالب في خانة الملاحظات في Instapay
    notes_code = models.CharField(max_length=100, unique=True)

    # بيانات إضافية من فورم التأكيد
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    user_note = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.plan} - {self.status}"


class UserStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streak")
    current_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
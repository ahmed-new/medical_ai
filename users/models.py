from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator



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





class UserStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streak")
    current_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)